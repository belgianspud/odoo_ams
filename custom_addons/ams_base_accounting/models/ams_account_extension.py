class AmsAccountExtension(models.Model):
    """
    Extend account.account to add association-specific features
    """
    _inherit = 'account.account'
    
    # Association-specific fields
    is_ams_account = fields.Boolean(string='AMS Account', default=False)
    ams_account_type = fields.Selection([
        ('membership_revenue', 'Membership Revenue'),
        ('event_revenue', 'Event Revenue'),
        ('donation_revenue', 'Donation Revenue'),
        ('operational_expense', 'Operational Expense'),
        ('program_expense', 'Program Expense'),
        ('administrative_expense', 'Administrative Expense'),
        ('member_receivable', 'Member Receivables'),
        ('event_receivable', 'Event Receivables'),
        ('deferred_revenue', 'Deferred Revenue'),
    ], string='AMS Account Type')
    
    revenue_category_id = fields.Many2one(
        'ams.revenue.category',
        string='Revenue Category'
    )