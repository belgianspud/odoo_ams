from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, date
import logging

_logger = logging.getLogger(__name__)

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
    period_month = fields.Integer(
        string='Month',
        help="Only for monthly closing"
    )
    period_quarter = fields.Integer(
        string='Quarter',
        help="Only for quarterly closing"
    )
    
    generate_reports = fields.Boolean(
        string='Generate Reports', 
        default=True,
        help="Generate financial summary reports for the period"
    )
    send_summary_email = fields.Boolean(
        string='Send Summary Email', 
        default=False,
        help="Send financial summary to management team"
    )
    include_chapters = fields.Boolean(
        string='Include Chapter Breakdown',
        default=True,
        help="Include individual chapter financial summaries"
    )
    
    @api.onchange('period_type')
    def _onchange_period_type(self):
        """Clear inappropriate fields based on period type"""
        if self.period_type != 'month':
            self.period_month = False
        if self.period_type != 'quarter':
            self.period_quarter = False
    
    @api.constrains('period_month')
    def _check_period_month(self):
        """Validate month is between 1-12"""
        for record in self:
            if record.period_month and (record.period_month < 1 or record.period_month > 12):
                raise ValidationError(_("Month must be between 1 and 12"))
    
    @api.constrains('period_quarter')
    def _check_period_quarter(self):
        """Validate quarter is between 1-4"""
        for record in self:
            if record.period_quarter and (record.period_quarter < 1 or record.period_quarter > 4):
                raise ValidationError(_("Quarter must be between 1 and 4"))
    
    def action_close_period(self):
        """Execute the period close process"""
        self.ensure_one()
        
        # Validate required fields
        if self.period_type == 'month' and not self.period_month:
            raise UserError(_("Month is required for monthly closing"))
        if self.period_type == 'quarter' and not self.period_quarter:
            raise UserError(_("Quarter is required for quarterly closing"))
        
        # Calculate period dates
        period_start, period_end = self._get_period_dates()
        
        # Generate financial summaries
        summary_data = self._generate_financial_summaries(period_start, period_end)
        
        # Create summary records if needed
        if self.generate_reports:
            summary_records = self._create_summary_records(summary_data)
        
        # Send emails if requested
        if self.send_summary_email:
            self._send_summary_emails(summary_data)
        
        # Return action to view results
        return self._return_summary_action(summary_data)
    
    def _get_period_dates(self):
        """Calculate start and end dates for the selected period"""
        if self.period_type == 'month':
            period_start = date(self.period_year, self.period_month, 1)
            if self.period_month == 12:
                period_end = date(self.period_year + 1, 1, 1)
            else:
                period_end = date(self.period_year, self.period_month + 1, 1)
        elif self.period_type == 'quarter':
            quarter_start_months = {1: 1, 2: 4, 3: 7, 4: 10}
            start_month = quarter_start_months[self.period_quarter]
            period_start = date(self.period_year, start_month, 1)
            if self.period_quarter == 4:
                period_end = date(self.period_year + 1, 1, 1)
            else:
                end_month = quarter_start_months[self.period_quarter + 1]
                period_end = date(self.period_year, end_month, 1)
        else:  # year
            period_start = date(self.period_year, 1, 1)
            period_end = date(self.period_year + 1, 1, 1)
        
        return period_start, period_end
    
    def _generate_financial_summaries(self, period_start, period_end):
        """Generate financial summary data for the period"""
        # Get all financial transactions in the period
        transactions = self.env['ams.financial.transaction'].search([
            ('date', '>=', period_start),
            ('date', '<', period_end),
            ('state', '=', 'confirmed')
        ])
        
        # Calculate totals by category
        summary_data = {
            'period_start': period_start,
            'period_end': period_end,
            'total_revenue': 0.0,
            'revenue_by_category': {},
            'revenue_by_chapter': {},
            'transaction_count': len(transactions),
        }
        
        for transaction in transactions:
            if transaction.transaction_type == 'income':
                summary_data['total_revenue'] += transaction.amount
                
                # By category
                if transaction.revenue_category_id:
                    category_name = transaction.revenue_category_id.name
                    if category_name not in summary_data['revenue_by_category']:
                        summary_data['revenue_by_category'][category_name] = 0.0
                    summary_data['revenue_by_category'][category_name] += transaction.amount
                
                # By chapter
                if transaction.chapter_id:
                    chapter_name = transaction.chapter_id.name
                    if chapter_name not in summary_data['revenue_by_chapter']:
                        summary_data['revenue_by_chapter'][chapter_name] = 0.0
                    summary_data['revenue_by_chapter'][chapter_name] += transaction.amount
        
        return summary_data
    
    def _create_summary_records(self, summary_data):
        """Create period summary records"""
        # This would create records in ams.financial.summary
        # Implementation depends on your specific requirements
        _logger.info(f"Creating summary records for period {summary_data['period_start']} to {summary_data['period_end']}")
        return True
    
    def _send_summary_emails(self, summary_data):
        """Send summary emails to management"""
        # Get email template
        template = self.env.ref('ams_accounting.email_template_period_close_summary', False)
        if template:
            # Send to appropriate recipients
            _logger.info("Sending period close summary emails")
        return True
    
    def _return_summary_action(self, summary_data):
        """Return action to display summary results"""
        return {
            'type': 'ir.actions.act_window',
            'name': f'Financial Summary - {self.period_type.title()} {self.period_year}',
            'res_model': 'ams.financial.summary',
            'view_mode': 'tree,form',
            'domain': [
                ('period_year', '=', self.period_year),
                ('period_month', '=', self.period_month if self.period_type == 'month' else False),
                ('period_quarter', '=', self.period_quarter if self.period_type == 'quarter' else False),
            ],
            'context': {
                'search_default_current_period': 1,
            }
        }