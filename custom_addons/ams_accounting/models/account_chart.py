from odoo import models, fields, api
from odoo.exceptions import ValidationError

class AccountAccount(models.Model):
    _inherit = 'account.account'
    
    # AMS-specific fields
    is_ams_account = fields.Boolean('AMS Account', default=False,
                                   help="Mark this account for use in AMS accounting")
    ams_account_type = fields.Selection([
        ('membership_revenue', 'Membership Revenue'),
        ('chapter_revenue', 'Chapter Revenue'),
        ('publication_revenue', 'Publication Revenue'),
        ('subscription_receivable', 'Subscription Receivable'),
        ('deferred_revenue', 'Deferred Revenue'),
        ('membership_expense', 'Membership Expense'),
        ('chapter_expense', 'Chapter Expense'),
        ('publication_expense', 'Publication Expense'),
        ('other', 'Other AMS Account')
    ], string='AMS Account Type', help="Categorize accounts for AMS reporting")
    
    # Product mappings
    subscription_product_ids = fields.One2many('product.account.mapping', 'account_id', 
                                              'Mapped Subscription Products')
    
    # Statistics
    ams_balance = fields.Float('AMS Balance', compute='_compute_ams_balance', store=True,
                              help="Balance for AMS-specific transactions")
    subscription_revenue_ytd = fields.Float('YTD Subscription Revenue', 
                                           compute='_compute_subscription_revenue', store=True)
    
    @api.depends('balance', 'move_line_ids.ams_subscription_id')
    def _compute_ams_balance(self):
        for account in self:
            # Calculate balance from AMS-related move lines
            ams_lines = account.move_line_ids.filtered(lambda l: l.ams_subscription_id)
            account.ams_balance = sum(ams_lines.mapped('balance'))
    
    @api.depends('move_line_ids.ams_subscription_id', 'move_line_ids.credit', 'move_line_ids.debit')
    def _compute_subscription_revenue(self):
        for account in self:
            # Calculate YTD subscription revenue
            current_year = fields.Date.today().year
            year_start = fields.Date.from_string(f'{current_year}-01-01')
            
            subscription_lines = account.move_line_ids.filtered(
                lambda l: l.ams_subscription_id and l.date >= year_start
            )
            
            if account.account_type in ['income', 'income_other']:
                account.subscription_revenue_ytd = sum(subscription_lines.mapped('credit')) - sum(subscription_lines.mapped('debit'))
            else:
                account.subscription_revenue_ytd = 0.0

class AMSAccountChart(models.Model):
    _name = 'ams.account.chart'
    _description = 'AMS Account Chart Template'
    _order = 'sequence, name'
    
    name = fields.Char('Chart Name', required=True)
    code = fields.Char('Chart Code', required=True)
    sequence = fields.Integer('Sequence', default=10)
    active = fields.Boolean('Active', default=True)
    description = fields.Text('Description')
    
    # Chart configuration
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', 'Currency', related='company_id.currency_id')
    
    # Account categories for AMS
    account_template_ids = fields.One2many('ams.account.template', 'chart_id', 'Account Templates')
    
    # Status
    is_installed = fields.Boolean('Installed', default=False)
    installation_date = fields.Datetime('Installation Date')
    
    def action_install_chart(self):
        """Install the chart of accounts"""
        if self.is_installed:
            raise ValidationError("This chart is already installed.")
        
        # Create accounts from templates
        for template in self.account_template_ids:
            template._create_account()
        
        self.write({
            'is_installed': True,
            'installation_date': fields.Datetime.now()
        })
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Success',
                'message': f'Chart of accounts "{self.name}" has been installed successfully.',
                'type': 'success',
                'sticky': False,
            }
        }
    
    def action_view_accounts(self):
        """View accounts created from this chart"""
        accounts = self.env['account.account'].search([
            ('code', '=like', f'{self.code}%'),
            ('company_id', '=', self.company_id.id)
        ])
        
        return {
            'type': 'ir.actions.act_window',
            'name': f'{self.name} - Accounts',
            'res_model': 'account.account',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', accounts.ids)],
            'context': {'search_default_is_ams_account': 1}
        }

class AMSAccountTemplate(models.Model):
    _name = 'ams.account.template'
    _description = 'AMS Account Template'
    _order = 'sequence, code'
    
    name = fields.Char('Account Name', required=True)
    code = fields.Char('Account Code', required=True)
    sequence = fields.Integer('Sequence', default=10)
    
    # Chart relationship
    chart_id = fields.Many2one('ams.account.chart', 'Chart', required=True, ondelete='cascade')
    
    # Account configuration
    account_type = fields.Selection([
        ('asset_receivable', 'Receivable'),
        ('asset_cash', 'Bank and Cash'),
        ('asset_current', 'Current Assets'),
        ('asset_non_current', 'Non-current Assets'),
        ('asset_prepayments', 'Prepayments'),
        ('asset_fixed', 'Fixed Assets'),
        ('liability_payable', 'Payable'),
        ('liability_credit_card', 'Credit Card'),
        ('liability_current', 'Current Liabilities'),
        ('liability_non_current', 'Non-current Liabilities'),
        ('equity', 'Equity'),
        ('equity_unaffected', 'Current Year Earnings'),
        ('income', 'Income'),
        ('income_other', 'Other Income'),
        ('expense', 'Expenses'),
        ('expense_depreciation', 'Depreciation'),
        ('expense_direct_cost', 'Cost of Revenue'),
        ('off_balance', 'Off-Balance Sheet'),
    ], string='Account Type', required=True)
    
    # AMS-specific fields
    ams_account_type = fields.Selection([
        ('membership_revenue', 'Membership Revenue'),
        ('chapter_revenue', 'Chapter Revenue'),
        ('publication_revenue', 'Publication Revenue'),
        ('subscription_receivable', 'Subscription Receivable'),
        ('deferred_revenue', 'Deferred Revenue'),
        ('membership_expense', 'Membership Expense'),
        ('chapter_expense', 'Chapter Expense'),
        ('publication_expense', 'Publication Expense'),
        ('other', 'Other AMS Account')
    ], string='AMS Account Type')
    
    # Configuration
    reconcile = fields.Boolean('Allow Reconciliation', default=False)
    deprecated = fields.Boolean('Deprecated', default=False)
    
    # Parent/child relationship for account hierarchy
    parent_id = fields.Many2one('ams.account.template', 'Parent Account')
    child_ids = fields.One2many('ams.account.template', 'parent_id', 'Child Accounts')
    
    # Account tags for grouping
    tag_ids = fields.Many2many('account.account.tag', 'ams_account_template_tag_rel',
                              'template_id', 'tag_id', 'Account Tags')
    
    def _create_account(self):
        """Create account.account from this template"""
        # Check if account already exists
        existing_account = self.env['account.account'].search([
            ('code', '=', self.code),
            ('company_id', '=', self.chart_id.company_id.id)
        ], limit=1)
        
        if existing_account:
            # Update existing account with AMS fields
            existing_account.write({
                'is_ams_account': True,
                'ams_account_type': self.ams_account_type,
            })
            return existing_account
        
        # Create new account
        account_vals = {
            'name': self.name,
            'code': self.code,
            'account_type': self.account_type,
            'company_id': self.chart_id.company_id.id,
            'reconcile': self.reconcile,
            'deprecated': self.deprecated,
            'is_ams_account': True,
            'ams_account_type': self.ams_account_type,
            'tag_ids': [(6, 0, self.tag_ids.ids)],
        }
        
        account = self.env['account.account'].create(account_vals)
        return account
    
    @api.constrains('code', 'chart_id')
    def _check_unique_code(self):
        for template in self:
            duplicate = self.search([
                ('code', '=', template.code),
                ('chart_id', '=', template.chart_id.id),
                ('id', '!=', template.id)
            ])
            if duplicate:
                raise ValidationError(f"Account code '{template.code}' already exists in this chart.")
    
    _sql_constraints = [
        ('code_chart_unique', 'unique(code, chart_id)', 
         'Account code must be unique within a chart!'),
    ]