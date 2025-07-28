class FinancialPeriodClose(models.TransientModel):
    """Wizard to close financial periods and generate reports"""
    _name = 'ams.financial.period.close'
    _description = 'Financial Period Close Wizard'
    
    period_type = fields.Selection([
        ('month', 'Monthly'),
        ('quarter', 'Quarterly'),
        ('year', 'Yearly'),
    ], string='Period Type', required=True, default='month')
    
    period_year = fields.Integer(
        string='Year',
        required=True,
        default=lambda self: fields.Date.today().year
    )
    period_month = fields.Integer(string='Month')
    period_quarter = fields.Integer(string='Quarter')
    
    generate_reports = fields.Boolean(string='Generate Reports', default=True)
    send_summary_email = fields.Boolean(string='Send Summary Email', default=False)
    
    def action_close_period(self):
        """Close the financial period and generate summary"""
        # Create period close record
        # Generate financial summaries
        # Send reports if requested
        return {
            'type': 'ir.actions.act_window',
            'name': 'Financial Summary',
            'res_model': 'ams.financial.summary',
            'view_mode': 'tree,form',
            'domain': [
                ('period_year', '=', self.period_year),
                ('period_month', '=', self.period_month if self.period_type == 'month' else False),
                ('period_quarter', '=', self.period_quarter if self.period_type == 'quarter' else False),
            ],
        }
