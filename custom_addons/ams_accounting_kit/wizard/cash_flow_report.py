from odoo import api, fields, models
from odoo.tools.misc import get_lang


class AccountingReport(models.TransientModel):
    _name = "cash.flow.report"
    # Removed inheritance from account.report to avoid Many2many conflicts
    _description = "Cash Flow Report"

    name = fields.Char(string="Cash Flow Report", default="Cash Flow Report", required=True, translate=True)
    date_from = fields.Date(string='Start Date')
    date_to = fields.Date(string='End Date')
    company_id = fields.Many2one('res.company', string='Company', required=True, readonly=True, default=lambda self: self.env.company)
    target_move = fields.Selection([('posted', 'All Posted Entries'),
                                    ('all', 'All Entries'),
                                    ], string='Target Moves', required=True, default='posted')
    journal_ids = fields.Many2many(
        comodel_name='account.journal',
        relation='cash_flow_report_journal_rel',  # Explicit relation name
        column1='report_id',
        column2='journal_id',
        string='Journals',
        required=True,
        default=lambda self: self.env['account.journal'].search([('company_id', '=', self.company_id.id)]),
        domain="[('company_id', '=', company_id)]",
    )

    @api.model
    def _get_account_report(self):
        reports = []
        if self._context.get('active_id'):
            menu = self.env['ir.ui.menu'].browse(
                self._context.get('active_id')).name
            reports = self.env['account.financial.report'].search(
                [('name', 'ilike', menu)])
        return reports and reports[0] or False

    enable_filter = fields.Boolean(string='Enable Comparison')
    account_report_id = fields.Many2one('account.financial.report',
                                        string='Account Reports',
                                        required=True,
                                        default=_get_account_report)
    label_filter = fields.Char(string='Column Label',
                               help="This label will be displayed on report to show the balance"
                                    " computed for the given comparison filter.")
    filter_cmp = fields.Selection(
        [('filter_no', 'No Filters'), ('filter_date', 'Date')],
        string='Filter by', required=True, default='filter_no')
    date_from_cmp = fields.Date(string='Date Start')
    date_to_cmp = fields.Date(string='Date End')
    debit_credit = fields.Boolean(string='Display Debit/Credit Columns',
                                  help="This option allows you to get more details about the way your balances are computed. Because it is space consuming, we do not allow to use it while doing a comparison.")

    @api.onchange('company_id')
    def _onchange_company_id(self):
        if self.company_id:
            self.journal_ids = self.env['account.journal'].search(
                [('company_id', '=', self.company_id.id)])
        else:
            self.journal_ids = self.env['account.journal'].search([])

    def _build_comparison_context(self, data):
        result = {}
        result['journal_ids'] = 'journal_ids' in data['form'] and data['form'][
            'journal_ids'] or False
        result['state'] = 'target_move' in data['form'] and data['form'][
            'target_move'] or ''
        if data['form']['filter_cmp'] == 'filter_date':
            result['date_from'] = data['form']['date_from_cmp']
            result['date_to'] = data['form']['date_to_cmp']
            result['strict_range'] = True
        return result

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
        data['form'] = self.read(
            ['account_report_id', 'date_from', 'date_to', 'date_from_cmp', 'date_to_cmp',
             'journal_ids', 'filter_cmp', 'target_move', 'company_id'])[0]
        for field in ['account_report_id']:
            if isinstance(data['form'][field], tuple):
                data['form'][field] = data['form'][field][0]
        comparison_context = self._build_comparison_context(data)
        used_context = self._build_contexts(data)
        data['form']['used_context'] = dict(used_context, lang=get_lang(self.env).code)
        data['form']['comparison_context'] = comparison_context
        return self.with_context(discard_logo_check=True)._print_report(data)

    def _print_report(self, data):
        data['form'].update(self.read(
            ['date_from_cmp', 'debit_credit', 'date_to_cmp', 'filter_cmp',
             'account_report_id', 'enable_filter', 'label_filter',
             'target_move'])[0])
        return self.env.ref(
            'ams_accounting_kit.action_report_cash_flow').report_action(self,
                                                                         data=data,
                                                                         config=False)