from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)

class AmsRevenueCategory(models.Model):
    """Revenue categories for association financial tracking"""
    _name = 'ams.revenue.category'
    _description = 'AMS Revenue Category'
    _order = 'sequence, name'
    _rec_name = 'name'

    name = fields.Char(string='Category Name', required=True, tracking=True)
    code = fields.Char(string='Category Code', required=True, size=10)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True, tracking=True)
    
    description = fields.Text(string='Description')
    color = fields.Integer(string='Color Index', default=0)
    
    # Account mapping for integration
    income_account_id = fields.Many2one(
        'account.account', 
        string='Income Account',
        domain=[('account_type', '=', 'income')],
        help="Default income account for this revenue category",
        tracking=True
    )
    
    # Category classification
    category_type = fields.Selection([
        ('membership', 'Membership Revenue'),
        ('event', 'Event Revenue'),
        ('donation', 'Donations'),
        ('sponsorship', 'Sponsorships'),
        ('merchandise', 'Merchandise Sales'),
        ('training', 'Training/Education'),
        ('certification', 'Certification Fees'),
        ('other', 'Other Revenue')
    ], string='Category Type', required=True, tracking=True)
    
    # Financial planning
    budget_amount = fields.Monetary(
        string='Annual Budget', 
        currency_field='currency_id',
        help="Budgeted amount for this category this year",
        tracking=True
    )
    currency_id = fields.Many2one(
        'res.currency', 
        default=lambda self: self.env.company.currency_id
    )
    
    # Computed statistics (simplified to avoid circular dependencies)
    current_year_revenue = fields.Monetary(
        string='Current Year Revenue', 
        compute='_compute_revenue_stats',
        currency_field='currency_id'
    )
    transaction_count = fields.Integer(
        string='Transaction Count',
        compute='_compute_revenue_stats'
    )
    budget_variance = fields.Monetary(
        string='Budget Variance',
        compute='_compute_revenue_stats',
        currency_field='currency_id',
        help="Actual vs budgeted amount"
    )
    budget_percentage = fields.Float(
        string='Budget Achievement %',
        compute='_compute_revenue_stats',
        help="Percentage of budget achieved"
    )
    
    def _compute_revenue_stats(self):
        """Compute revenue statistics for the current year"""
        current_year = fields.Date.today().year
        
        for category in self:
            # Initialize defaults
            category.current_year_revenue = 0.0
            category.transaction_count = 0
            category.budget_variance = 0.0
            category.budget_percentage = 0.0
            
            # Try to get transactions (may not exist if ams_financial_transaction isn't loaded)
            try:
                transactions = self.env['ams.financial.transaction'].search([
                    ('revenue_category_id', '=', category.id),
                    ('transaction_type', '=', 'income'),
                    ('state', '=', 'confirmed'),
                    ('date', '>=', f'{current_year}-01-01'),
                    ('date', '<=', f'{current_year}-12-31'),
                ])
                
                category.current_year_revenue = sum(transactions.mapped('amount'))
                category.transaction_count = len(transactions)
                
                # Budget calculations
                if category.budget_amount:
                    category.budget_variance = category.current_year_revenue - category.budget_amount
                    category.budget_percentage = (category.current_year_revenue / category.budget_amount) * 100
                    
            except Exception as e:
                # If financial transaction model doesn't exist yet, just use defaults
                _logger.debug(f"Could not compute revenue stats for category {category.name}: {e}")
                pass
    
    # REMOVED: Direct One2many relationship to avoid circular dependency during loading
    # transaction_ids = fields.One2many(
    #     'ams.financial.transaction', 
    #     'revenue_category_id', 
    #     string='Financial Transactions'
    # )
    
    @api.constrains('code')
    def _check_unique_code(self):
        """Ensure category codes are unique"""
        for record in self:
            if self.search_count([('code', '=', record.code), ('id', '!=', record.id)]) > 0:
                raise ValidationError(_("Revenue category code '%s' must be unique!") % record.code)
    
    @api.constrains('budget_amount')
    def _check_budget_amount(self):
        """Ensure budget amount is positive"""
        for record in self:
            if record.budget_amount < 0:
                raise ValidationError(_("Budget amount must be positive"))
    
    def action_view_transactions(self):
        """Action to view transactions for this category"""
        return {
            'type': 'ir.actions.act_window',
            'name': f'{self.name} - Transactions',
            'res_model': 'ams.financial.transaction',
            'view_mode': 'list,form',
            'domain': [('revenue_category_id', '=', self.id)],
            'context': {
                'default_revenue_category_id': self.id,
                'search_default_current_year': 1,
            }
        }