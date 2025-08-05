# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError

class AccountJournal(models.Model):
    _name = 'ams.account.journal'
    _description = 'AMS Accounting Journals'
    _order = 'sequence, name'
    
    name = fields.Char(
        string='Journal Name',
        required=True,
        translate=True,
        help='Name of the journal'
    )
    
    code = fields.Char(
        string='Short Code',
        size=5,
        required=True,
        help='Short code for the journal (max 5 characters)'
    )
    
    type = fields.Selection([
        ('sale', 'Sales'),
        ('purchase', 'Purchase'),
        ('cash', 'Cash'),
        ('bank', 'Bank'),
        ('general', 'General'),
        ('membership', 'Membership'),
        ('chapter', 'Chapter'),
        ('publication', 'Publication'),
        ('deferred_revenue', 'Deferred Revenue'),
    ], string='Type', required=True,
       help='Type of journal determines its usage and behavior')
    
    sequence = fields.Integer(
        string='Sequence',
        default=10,
        help='Used to order journals in selection lists'
    )
    
    active = fields.Boolean(
        string='Active',
        default=True,
        help='Inactive journals are hidden from selection'
    )
    
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company
    )
    
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        help='Journal currency if different from company currency'
    )
    
    # Default accounts for this journal type
    default_account_id = fields.Many2one(
        'ams.account.account',
        string='Default Account',
        help='Default account for journal entries in this journal'
    )
    
    # AMS-specific configurations
    is_ams_journal = fields.Boolean(
        string='AMS Journal',
        default=True,
        help='This journal is managed by AMS accounting'
    )
    
    auto_post = fields.Boolean(
        string='Auto Post Entries',
        default=False,
        help='Automatically post journal entries created in this journal'
    )
    
    # Subscription-specific settings
    subscription_journal = fields.Boolean(
        string='Subscription Journal',
        help='This journal is used for subscription-related transactions'
    )
    
    revenue_recognition_journal = fields.Boolean(
        string='Revenue Recognition Journal',
        help='This journal is used for revenue recognition entries'
    )
    
    # Entry sequence settings
    sequence_id = fields.Many2one(
        'ir.sequence',
        string='Entry Sequence',
        help='Sequence used for journal entry numbering'
    )
    
    # Security and controls
    restrict_mode_hash_table = fields.Boolean(
        string='Lock Posted Entries',
        default=True,
        help='Lock posted entries to prevent modification'
    )
    
    # Journal entries
    move_ids = fields.One2many(
        'ams.account.move',
        'journal_id',
        string='Journal Entries',
        readonly=True
    )
    
    # Statistics
    entries_count = fields.Integer(
        string='Entries Count',
        compute='_compute_entries_count'
    )
    
    @api.depends('move_ids')
    def _compute_entries_count(self):
        """Compute number of journal entries"""
        for journal in self:
            journal.entries_count = len(journal.move_ids)
    
    @api.constrains('code', 'company_id')
    def _check_code_company_unique(self):
        """Ensure journal codes are unique per company"""
        for journal in self:
            if self.search_count([
                ('code', '=', journal.code),
                ('company_id', '=', journal.company_id.id),
                ('id', '!=', journal.id)
            ]) > 0:
                raise ValidationError(f'Journal code "{journal.code}" already exists for company "{journal.company_id.name}"')
    
    @api.model_create_multi
    def create(self, vals_list):
        """Override create to set up sequences and defaults"""
        journals = super().create(vals_list)
        
        for journal in journals:
            if not journal.sequence_id:
                journal._create_sequence()
        
        return journals
    
    def _create_sequence(self):
        """Create sequence for journal entry numbering"""
        self.ensure_one()
        
        sequence_vals = {
            'name': f'{self.name} Sequence',
            'code': f'ams.journal.{self.code.lower()}',
            'prefix': f'{self.code}/',
            'suffix': '',
            'number_next': 1,
            'number_increment': 1,
            'padding': 4,
            'company_id': self.company_id.id,
        }
        
        sequence = self.env['ir.sequence'].create(sequence_vals)
        self.sequence_id = sequence.id
    
    def name_get(self):
        """Display format: [CODE] Journal Name"""
        result = []
        for journal in self:
            name = f'[{journal.code}] {journal.name}'
            result.append((journal.id, name))
        return result
    
    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        """Allow searching by code or name"""
        args = args or []
        if name:
            domain = ['|', ('code', operator, name), ('name', operator, name)]
            journal_ids = self._search(domain + args, limit=limit, access_rights_uid=name_get_uid)
            return self.browse(journal_ids).name_get()
        return super()._name_search(name, args=args, operator=operator, limit=limit, name_get_uid=name_get_uid)
    
    def action_view_entries(self):
        """Action to view journal entries for this journal"""
        self.ensure_one()
        
        return {
            'name': f'Journal Entries - {self.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'ams.account.move',
            'view_mode': 'list,form',
            'domain': [('journal_id', '=', self.id)],
            'context': {
                'default_journal_id': self.id,
                'search_default_journal_id': self.id,
            }
        }
    
    def action_create_entry(self):
        """Action to create new journal entry in this journal"""
        self.ensure_one()
        
        return {
            'name': f'New Entry - {self.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'ams.account.move',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_journal_id': self.id,
                'default_move_type': 'entry',
            }
        }
    
    @api.model
    def create_default_journals(self, company_id=None):
        """Create default journals for AMS"""
        if not company_id:
            company_id = self.env.company.id
        
        # Get default accounts (create if needed)
        account_model = self.env['ams.account.account']
        cash_account = account_model.search([
            ('code', '=', '1000'),
            ('company_id', '=', company_id)
        ], limit=1)
        
        if not cash_account:
            # Create default accounts first
            account_model.create_default_accounts(company_id)
            cash_account = account_model.search([
                ('code', '=', '1000'),
                ('company_id', '=', company_id)
            ], limit=1)
        
        # Define default journals
        default_journals = [
            {
                'name': 'Membership Sales',
                'code': 'MEMB',
                'type': 'membership',
                'sequence': 10,
                'subscription_journal': True,
                'auto_post': False,
            },
            {
                'name': 'Chapter Operations',
                'code': 'CHAP',
                'type': 'chapter',
                'sequence': 20,
            },
            {
                'name': 'Publication Sales',
                'code': 'PUB',
                'type': 'publication',
                'sequence': 30,
                'subscription_journal': True,
            },
            {
                'name': 'Revenue Recognition',
                'code': 'REVR',
                'type': 'deferred_revenue',
                'sequence': 40,
                'revenue_recognition_journal': True,
                'auto_post': True,
            },
            {
                'name': 'General Journal',
                'code': 'GEN',
                'type': 'general',
                'sequence': 50,
                'default_account_id': cash_account.id if cash_account else False,
            },
            {
                'name': 'Cash Receipts',
                'code': 'CASH',
                'type': 'cash',
                'sequence': 60,
                'default_account_id': cash_account.id if cash_account else False,
            },
        ]
        
        created_journals = self.env['ams.account.journal']
        
        for journal_data in default_journals:
            journal_data['company_id'] = company_id
            
            # Check if journal already exists
            existing = self.search([
                ('code', '=', journal_data['code']),
                ('company_id', '=', company_id)
            ])
            
            if not existing:
                journal = self.create(journal_data)
                created_journals |= journal
        
        return created_journals
    
    @api.model
    def get_subscription_journal(self):
        """Get the default subscription journal"""
        journal = self.search([
            ('subscription_journal', '=', True),
            ('company_id', '=', self.env.company.id)
        ], limit=1)
        
        if not journal:
            # Create default journals if none exist
            self.create_default_journals()
            journal = self.search([
                ('subscription_journal', '=', True),
                ('company_id', '=', self.env.company.id)
            ], limit=1)
        
        return journal
    
    @api.model
    def get_revenue_recognition_journal(self):
        """Get the revenue recognition journal"""
        journal = self.search([
            ('revenue_recognition_journal', '=', True),
            ('company_id', '=', self.env.company.id)
        ], limit=1)
        
        if not journal:
            # Create default journals if none exist
            self.create_default_journals()
            journal = self.search([
                ('revenue_recognition_journal', '=', True),
                ('company_id', '=', self.env.company.id)
            ], limit=1)
        
        return journal