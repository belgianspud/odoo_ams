from odoo import models, fields
from odoo.tools.misc import get_lang

class AccountTaxReport(models.TransientModel):
    # Removed inheritance from account.report to avoid Many2many conflicts
    _name = 'kit.account.tax.report'
    _description = 'Tax Report'
    
    company_id = fields.Many2one('res.company', string='Company', required=True, readonly=True, default=lambda self: self.env.company)
    name = fields.Char(string="Tax Report", default="Tax Report", required=True, translate=True)
    date_from = fields.Date(string='Start Date')
    date_to = fields.Date(string='End Date')
    journal_ids = fields.Many2many(
        comodel_name='account.journal',
        relation='kit_account_tax_report_journal_rel',  # Explicit relation name
        column1='report_id',
        column2='journal_id',
        string='Journals',
        required=True,
        default=lambda self: self.env['account.journal'].search([('company_id', '=', self.company_id.id)]),
        domain="[('company_id', '=', company_id)]",
    )
    target_move = fields.Selection([('posted', 'All Posted Entries'),
                                    ('all', 'All Entries'),
                                    ], string='Target Moves', required=True, default='posted')

    def _build_contexts(self, data):
        result = {}
        result['journal_ids'] = 'journal_ids' in data['form'] and data['form']['journal_ids'] or False
        result['state'] = 'target_move' in data['form'] and data['form']['target_move'] or ''
        result['date_from'] = data['form']['date_from'] or False
        result['date_to'] = data['form']['date_to'] or False
        result['strict_range'] = True if result['date_from'] else False
        result['company_id'] = data['form']['company_id'][0] if isinstance(data['form']['company_id'], (list, tuple)) else data['form']['company_id'] or False
        return result

    def check_report(self):
        self.ensure_one()
        data = {}
        data['ids'] = self.env.context.get('active_ids', [])
        data['model'] = self.env.context.get('active_model', 'ir.ui.menu')
        data['form'] = self.read(['date_from', 'date_to', 'journal_ids', 'target_move', 'company_id'])[0]
        used_context = self._build_contexts(data)
        data['form']['used_context'] = dict(used_context, lang=get_lang(self.env).code)
        return self.with_context(discard_logo_check=True)._print_report(data)

    def pre_print_report(self, data):
        data['form'].update(self.read(['display_account'])[0])
        return data

    def _print_report(self, data):
        return self.env.ref(
            'ams_accounting_kit.action_report_account_tax').report_action(
            self, data=data)