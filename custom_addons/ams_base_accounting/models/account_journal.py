# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError

class AMSAccountJournal(models.Model):
    """AMS Journal with Association-specific journal types"""
    _name = 'ams.account.journal'
    _description = 'AMS Journal'
    _order = 'sequence, type, code'
    _check_company_auto = True
    _inherit = ['mail.thread', 'mail.activity.mixin']
    
    # Basic Information
    name = fields.Char(string='Journal Name', required=True, tracking=True)
    code = fields.Char(string='Short Code', size=5, required=True, tracking=True, help="Unique code for the journal")
    
    # Journal Type
    type = fields.Selection([
        ('sale', 'Sales'),
        ('purchase', 'Purchase'),
        ('cash', 'Cash'),
        ('bank', 'Bank'),
        ('general', 'Miscellaneous'),
    ], string='Type', required=True, default='general', tracking=True)
    
    # AMS-Specific Journal Types
    ams_journal_type = fields.Selection([
        ('general', 'General'),
        ('membership', 'Membership'),
        ('chapter', 'Chapter'),
        ('publication', 'Publication'),
        ('revenue_recognition', 'Revenue Recognition'),
        ('event', 'Event'),
    ], string='AMS Journal Type', default='general', required=True, tracking=True)
    
    # Settings
    active = fields.Boolean(string='Active', default=True, tracking=True)
    
    sequence = fields.Integer(string='Sequence', default=10, help="Used to order journals in the dashboard")
    
    color = fields.Integer(string='Color', default=0, help="Color for the journal in kanban view")
    
    # Default Account
    default_account_id = fields.Many2one(
        'ams.account.account',
        string='Default Account',
        ondelete='restrict',
        domain="[('deprecated', '=', False), ('company_id', '=', company_id)]",
        tracking=True,
        help="Default account for journal entries"
    )
    
    # Company
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        readonly=True,
        default=lambda self: self.env.company
    )
    
    # Sequence
    sequence_id = fields.Many2one(
        'ir.sequence',
        string='Entry Sequence',
        help="Sequence for journal entry numbers",
        copy=False
    )
    
    # Dashboard Settings
    show_on_dashboard = fields.Boolean(
        string='Show on Dashboard',
        default=True,
        help="Show this journal on the accounting dashboard"
    )
    
    kanban_dashboard = fields.Text(string='Kanban Dashboard', compute='_compute_kanban_dashboard')
    
    # Journal Entries Count
    entries_count = fields.Integer(string='Journal Entries', compute='_compute_entries_count')
    
    # Currency
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        help="The currency used to enter statement",
        default=lambda self: self.env.company.currency_id
    )
    
    # Automation Settings
    auto_post = fields.Boolean(
        string='Auto-Post Entries',
        default=False,
        help="Automatically post entries in this journal"
    )
    
    restrict_mode_hash_table = fields.Boolean(
        string='Lock Posted Entries',
        default=False,
        help="Forbid cancellation of journal entries"
    )
    
    # Journal Configuration
    update_posted = fields.Boolean(
        string='Allow Cancelling Entries',
        default=True,
        help="Check this box to allow the cancellation of journal entries"
    )
    
    at_least_one_inbound = fields.Boolean(string='At Least One Inbound', compute='_compute_at_least_one_inbound')
    at_least_one_outbound = fields.Boolean(string='At Least One Outbound', compute='_compute_at_least_one_outbound')
    
    # Constraints
    _sql_constraints = [
        ('code_company_uniq', 'unique (code, company_id)', 'Journal codes must be unique per company!'),
    ]
    
    @api.depends('type')
    def _compute_at_least_one_inbound(self):
        for journal in self:
            journal.at_least_one_inbound = journal.type in ('sale', 'cash', 'bank')
    
    @api.depends('type')
    def _compute_at_least_one_outbound(self):
        for journal in self:
            journal.at_least_one_outbound = journal.type in ('purchase', 'cash', 'bank')
    
    def _compute_entries_count(self):
        """Compute number of journal entries"""
        for journal in self:
            # Safe computation during module loading
            try:
                journal.entries_count = self.env['ams.account.move'].search_count([
                    ('journal_id', '=', journal.id)
                ])
            except:
                journal.entries_count = 0
    
    def _compute_kanban_dashboard(self):
        """Compute kanban dashboard data"""
        for journal in self:
            # Basic dashboard data
            dashboard_data = {
                'number_draft': 0,
                'number_posted': 0,
                'sum_draft': 0.0,
                'sum_posted': 0.0,
                'currency_symbol': journal.currency_id.symbol or '$',
            }
            journal.kanban_dashboard = str(dashboard_data)
    
    @api.constrains('type', 'ams_journal_type')
    def _check_journal_type_consistency(self):
        """Check consistency between journal type and AMS type"""
        for journal in self:
            if journal.ams_journal_type == 'revenue_recognition' and journal.type != 'general':
                raise ValidationError("Revenue recognition journals must be of type 'Miscellaneous'")
    
    @api.constrains('default_account_id', 'type')
    def _check_default_account_type(self):
        """Check default account type matches journal type"""
        for journal in self:
            if not journal.default_account_id:
                continue
                
            account_type = journal.default_account_id.account_type
            journal_type = journal.type
            
            valid_combinations = {
                'sale': ['income', 'income_membership', 'income_chapter', 'income_publication', 'income_other'],
                'purchase': ['expense', 'expense_depreciation', 'expense_direct_cost'],
                'cash': ['asset_cash'],
                'bank': ['asset_cash'],
                'general': ['asset_receivable', 'liability_payable', 'equity', 'income', 'expense'],
            }
            
            if journal_type in valid_combinations:
                if account_type not in valid_combinations[journal_type]:
                    raise ValidationError(
                        f"Default account type '{account_type}' is not compatible with journal type '{journal_type}'"
                    )
    
    def name_get(self):
        """Custom display name"""
        result = []
        for journal in self:
            name = f"[{journal.code}] {journal.name}"
            result.append((journal.id, name))
        return result
    
    @api.model
    def _name_search(self, name, domain=None, operator='ilike', limit=None, order=None):
        """Search by name or code"""
        if domain is None:
            domain = []
        
        if name:
            journals = self.search([
                '|',
                ('code', operator, name),
                ('name', operator, name)
            ] + domain, limit=limit, order=order)
            return journals.ids
        
        return super()._name_search(name, domain, operator, limit, order)
    
    @api.model_create_multi
    def create(self, vals_list):
        """Override create to generate sequences"""
        journals = super().create(vals_list)
        
        for journal, vals in zip(journals, vals_list):
            if not journal.sequence_id:
                # Create sequence for this journal
                sequence_vals = {
                    'name': f"{journal.name} Sequence",
                    'code': f"ams.journal.{journal.code.lower()}",
                    'prefix': f"{journal.code}/%(year)s/",
                    'suffix': '',
                    'padding': 4,
                    'company_id': journal.company_id.id,
                }
                sequence = self.env['ir.sequence'].create(sequence_vals)
                journal.sequence_id = sequence.id
        
        return journals
    
    def copy(self, default=None):
        """Override copy to handle code uniqueness"""
        self.ensure_one()
        default = dict(default or {})
        
        if 'code' not in default:
            default['code'] = f"{self.code}2"
        if 'name' not in default:
            default['name'] = f"{self.name} (Copy)"
        
        default['sequence_id'] = False  # Will be created automatically
        
        return super().copy(default)
    
    def unlink(self):
        """Prevent deletion of journals with entries"""
        for journal in self:
            if journal.entries_count > 0:
                raise UserError(
                    f"You cannot delete journal '{journal.display_name}' "
                    "that has journal entries."
                )
        return super().unlink()
    
    # Actions
    def action_view_entries(self):
        """Action to view journal entries"""
        self.ensure_one()
        return {
            'name': f'Journal Entries - {self.display_name}',
            'type': 'ir.actions.act_window',
            'res_model': 'ams.account.move',
            'view_mode': 'tree,form',
            'domain': [('journal_id', '=', self.id)],
            'context': {
                'default_journal_id': self.id,
                'search_default_posted': 1,
            }
        }
    
    def action_create_entry(self):
        """Action to create new journal entry"""
        self.ensure_one()
        return {
            'name': f'New Journal Entry - {self.display_name}',
            'type': 'ir.actions.act_window',
            'res_model': 'ams.account.move',
            'view_mode': 'form',
            'context': {
                'default_journal_id': self.id,
                'default_move_type': 'entry',
            }
        }
    
    def open_dashboard(self):
        """Open journal dashboard"""
        return {
            'name': f'Dashboard - {self.display_name}',
            'type': 'ir.actions.act_window',
            'res_model': 'ams.account.move',
            'view_mode': 'kanban,tree,form',
            'domain': [('journal_id', '=', self.id)],
            'context': {
                'default_journal_id': self.id,
                'search_default_posted': 1,
            }
        }
    
    @api.model
    def create_default_journals(self, company_id):
        """Create default journals for a company"""
        if not company_id:
            return False
        
        company = self.env['res.company'].browse(company_id)
        
        default_journals = [
            {
                'name': 'Membership Sales',
                'code': 'MEMB',
                'type': 'sale',
                'ams_journal_type': 'membership',
                'sequence': 10,
            },
            {
                'name': 'Chapter Operations',
                'code': 'CHAP',
                'type': 'general',
                'ams_journal_type': 'chapter',
                'sequence': 20,
            },
            {
                'name': 'Publication Sales',
                'code': 'PUB',
                'type': 'sale',
                'ams_journal_type': 'publication',
                'sequence': 30,
            },
            {
                'name': 'Revenue Recognition',
                'code': 'REV',
                'type': 'general',
                'ams_journal_type': 'revenue_recognition',
                'sequence': 40,
            },
            {
                'name': 'Cash Receipts',
                'code': 'CASH',
                'type': 'cash',
                'ams_journal_type': 'general',
                'sequence': 50,
            },
            {
                'name': 'General Journal',
                'code': 'GEN',
                'type': 'general',
                'ams_journal_type': 'general',
                'sequence': 60,
            },
        ]
        
        created_journals = []
        for journal_data in default_journals:
            journal_data['company_id'] = company_id
            
            # Check if journal already exists
            existing = self.search([
                ('code', '=', journal_data['code']),
                ('company_id', '=', company_id)
            ], limit=1)
            
            if not existing:
                journal = self.create(journal_data)
                created_journals.append(journal)
        
        return created_journals