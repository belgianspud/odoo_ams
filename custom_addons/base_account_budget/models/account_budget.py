from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class AccountBudgetPost(models.Model):
    _name = "account.budget.post"
    _order = "name"
    _description = "Budgetary Position"

    name = fields.Char('Name', required=True)
    account_ids = fields.Many2many('account.account', 'account_budget_rel',
                                   'budget_id', 'account_id', 'Accounts',
                                   domain=[('deprecated', '=', False)])
    budget_line = fields.One2many('budget.lines', 'general_budget_id',
                                  'Budget Lines')
    company_id = fields.Many2one('res.company', 'Company', required=True,
                                 default=lambda self: self.env.company)

    def _check_account_ids(self, vals):
        for val in vals:
            if 'account_ids' in val:
                account_ids = val['account_ids']
            else:
                account_ids = self.account_ids
            if not account_ids:
                raise ValidationError(
                    _('The budget must have at least one account.'))

    @api.model_create_multi
    def create(self, vals):
        self._check_account_ids(vals)
        return super(AccountBudgetPost, self).create(vals)

    def write(self, vals):
        self._check_account_ids([vals])
        return super(AccountBudgetPost, self).write(vals)


class Budget(models.Model):
    _name = "budget.budget"
    _description = "Budget"
    _inherit = ['mail.thread']

    name = fields.Char('Budget Name', required=True, readonly=True, states={'draft': [('readonly', False)]})
    creating_user_id = fields.Many2one('res.users', 'Responsible',
                                       default=lambda self: self.env.user)
    date_from = fields.Date('Start Date', required=True, readonly=True, states={'draft': [('readonly', False)]})
    date_to = fields.Date('End Date', required=True, readonly=True, states={'draft': [('readonly', False)]})
    state = fields.Selection([
        ('draft', 'Draft'),
        ('cancel', 'Cancelled'),
        ('confirm', 'Confirmed'),
        ('validate', 'Validated'),
        ('done', 'Done')
    ], 'Status', default='draft', index=True, required=True, readonly=True,
        copy=False, tracking=True)
    budget_line = fields.One2many('budget.lines', 'budget_id', 'Budget Lines',
                                  readonly=True, states={'draft': [('readonly', False)]},
                                  copy=True)
    company_id = fields.Many2one('res.company', 'Company', required=True,
                                 default=lambda self: self.env.company)

    def action_budget_confirm(self):
        self.write({'state': 'confirm'})

    def action_budget_draft(self):
        self.write({'state': 'draft'})

    def action_budget_validate(self):
        self.write({'state': 'validate'})

    def action_budget_cancel(self):
        self.write({'state': 'cancel'})

    def action_budget_done(self):
        self.write({'state': 'done'})


class BudgetLines(models.Model):
    _name = "budget.lines"
    _rec_name = "budget_id"
    _description = "Budget Line"

    budget_id = fields.Many2one('budget.budget', 'Budget', ondelete='cascade',
                                index=True, required=True)
    analytic_account_id = fields.Many2one('account.analytic.account',
                                          'Analytic Account')
    general_budget_id = fields.Many2one('account.budget.post',
                                        'Budgetary Position', required=True)
    date_from = fields.Date('Start Date', required=True)
    date_to = fields.Date('End Date', required=True)
    paid_date = fields.Date('Paid Date')
    planned_amount = fields.Float('Planned Amount', required=True)
    practical_amount = fields.Float(compute='_compute_practical_amount',
                                    string='Practical Amount')
    theoretical_amount = fields.Float(compute='_compute_theoretical_amount',
                                      string='Theoretical Amount')
    percentage = fields.Float(compute='_compute_percentage',
                              string='Achievement')
    company_id = fields.Many2one(related='budget_id.company_id',
                                 comodel_name='res.company',
                                 string='Company', store=True, readonly=True)

    @api.model
    def default_get(self, fields_list):
        """Set default analytic account from context"""
        result = super().default_get(fields_list)
        if self.env.context.get('default_analytic_account_id'):
            result['analytic_account_id'] = self.env.context.get('default_analytic_account_id')
        return result

    def _compute_practical_amount(self):
        for line in self:
            result = 0.0
            acc_ids = line.general_budget_id.account_ids.ids
            date_to = self.env.context.get('wizard_date_to') or line.date_to
            date_from = self.env.context.get(
                'wizard_date_from') or line.date_from
            if line.analytic_account_id.id:
                self.env.cr.execute("""
                    SELECT SUM(amount)
                    FROM account_analytic_line
                    WHERE account_id=%s
                        AND date between %s AND %s
                        AND general_account_id=ANY(%s)""",
                                    (line.analytic_account_id.id, date_from,
                                     date_to, acc_ids,))
                result = self.env.cr.fetchone()[0] or 0.0
            line.practical_amount = result

    def _compute_theoretical_amount(self):
        today = fields.Datetime.now()
        for line in self:
            # Used for the report

            if self.env.context.get(
                    'wizard_date_from') and self.env.context.get(
                    'wizard_date_to'):
                date_from = fields.Datetime.from_string(
                    self.env.context.get('wizard_date_from'))
                date_to = fields.Datetime.from_string(
                    self.env.context.get('wizard_date_to'))
                if date_from < fields.Datetime.from_string(line.date_from):
                    date_from = fields.Datetime.from_string(line.date_from)
                elif date_from > fields.Datetime.from_string(line.date_to):
                    date_from = False

                if date_to > fields.Datetime.from_string(line.date_to):
                    date_to = fields.Datetime.from_string(line.date_to)
                elif date_to < fields.Datetime.from_string(line.date_from):
                    date_to = False

                theo_amt = 0.00
                if date_from and date_to:
                    line_timedelta = fields.Datetime.from_string(
                        line.date_to) - fields.Datetime.from_string(
                        line.date_from)
                    elapsed_timedelta = date_to - date_from
                    if elapsed_timedelta.days > 0:
                        theo_amt = (
                                           elapsed_timedelta.total_seconds() / line_timedelta.total_seconds()) * line.planned_amount
            else:
                if line.paid_date:
                    if fields.Datetime.from_string(
                            line.date_to) <= fields.Datetime.from_string(
                            line.paid_date):
                        theo_amt = 0.00
                    else:
                        theo_amt = line.planned_amount
                else:
                    line_timedelta = fields.Datetime.from_string(
                        line.date_to) - fields.Datetime.from_string(
                        line.date_from)
                    elapsed_timedelta = fields.Datetime.from_string(today) - (
                        fields.Datetime.from_string(line.date_from))

                    if elapsed_timedelta.days < 0:
                        # If the budget line has not started yet, theoretical amount should be zero
                        theo_amt = 0.00
                    elif line_timedelta.days > 0 and fields.Datetime.from_string(
                            today) < fields.Datetime.from_string(
                            line.date_to):
                        # If today is between the budget line date_from and date_to
                        theo_amt = (
                                           elapsed_timedelta.total_seconds() / line_timedelta.total_seconds()) * line.planned_amount
                    else:
                        theo_amt = line.planned_amount

            line.theoretical_amount = theo_amt

    def _compute_percentage(self):
        for line in self:
            if line.theoretical_amount != 0.00:
                line.percentage = float((
                                                    line.practical_amount or 0.0) / line.theoretical_amount) * 100
            else:
                line.percentage = 0.00