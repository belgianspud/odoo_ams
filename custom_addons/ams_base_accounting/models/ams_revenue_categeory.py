# models/ams_revenue_category.py
from odoo import models, fields, api
from odoo.exceptions import ValidationError

class AmsRevenueCategory(models.Model):
    """
    Define revenue categories for association financial tracking.
    This allows categorizing income by source for better reporting.
    """
    _name = 'ams.revenue.category'
    _description = 'AMS Revenue Category'
    _order = 'sequence, name'

    name = fields.Char(string='Category Name', required=True)
    code = fields.Char(string='Category Code', required=True, size=10)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    
    description = fields.Text(string='Description')
    color = fields.Integer(string='Color Index', default=0)
    
    # Account mapping
    income_account_id = fields.Many2one(
        'account.account', 
        string='Income Account',
        domain=[('account_type', '=', 'income')]
    )
    
    # Category type
    category_type = fields.Selection([
        ('membership', 'Membership Revenue'),
        ('event', 'Event Revenue'),
        ('donation', 'Donations'),
        ('sponsorship', 'Sponsorships'),
        ('merchandise', 'Merchandise Sales'),
        ('training', 'Training/Education'),
        ('certification', 'Certification Fees'),
        ('other', 'Other Revenue')
    ], string='Category Type', required=True)
    
    # Financial tracking
    budget_amount = fields.Monetary(string='Annual Budget', currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id)
    
    # Statistics
    current_year_revenue = fields.Monetary(
        string='Current Year Revenue', 
        compute='_compute_revenue_stats',
        currency_field='currency_id'
    )
    transaction_count = fields.Integer(
        string='Transaction Count',
        compute='_compute_revenue_stats'
    )
    
    @api.depends('name')
    def _compute_revenue_stats(self):
        """Compute revenue statistics for the current year"""
        current_year = fields.Date.today().year
        for category in self:
            # This will be populated by actual transactions
            # For now, set to 0 - will be enhanced when transactions are tracked
            category.current_year_revenue = 0.0
            category.transaction_count = 0
    
    @api.constrains('code')
    def _check_unique_code(self):
        for record in self:
            if self.search_count([('code', '=', record.code), ('id', '!=', record.id)]) > 0:
                raise ValidationError(f"Revenue category code '{record.code}' must be unique!")
