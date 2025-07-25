from odoo import fields, models


class AccountPrintJournal(models.TransientModel):
    _inherit = "account.common.journal.report"
    _name = "account.print.journal"
    _description = "Account Print Journal"


    name = fields.Char(string="Journal Audit", default="Journal Audit", required=True, translate=True)
    sort_selection = fields.Selection(
        [('date', 'Date'), ('move_name', 'Journal Entry Number')],
        'Entries Sorted by', required=True, default='move_name')

    journal_ids = fields.Many2many(
        comodel_name='account.journal',
        relation='journal_audit_journal_rel',  # Unique relation table name
        column1='report_id',
        column2='journal_id',
        string='Journals',
        required=True,
        default=lambda self: self.env['account.journal'].search([('type', 'in', ['sale', 'purchase'])])
    )

    def _print_report(self, data):
        data = self.pre_print_report(data)
        data['form'].update({'sort_selection': self.sort_selection})
        return self.env.ref(
            'base_accounting_kit.action_report_journal').with_context(
            landscape=True).report_action(self, data=data)
