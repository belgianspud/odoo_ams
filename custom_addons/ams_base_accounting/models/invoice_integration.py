class AccountMoveAmsIntegration(models.Model):
    """Extend account.move (invoices) with AMS integration"""
    _inherit = 'account.move'
    
    # AMS categorization
    ams_revenue_category_id = fields.Many2one(
        'ams.revenue.category',
        string='AMS Revenue Category'
    )
    chapter_id = fields.Many2one(
        'res.partner',
        string='Chapter',
        domain=[('is_chapter', '=', True)]
    )
    
    # Auto-create financial transaction records
    @api.model_create_multi
    def create(self, vals_list):
        invoices = super().create(vals_list)
        for invoice in invoices:
            if invoice.move_type in ['out_invoice', 'in_invoice']:
                invoice._create_ams_transaction()
        return invoices
    
    def _create_ams_transaction(self):
        """Create AMS financial transaction record"""
        if self.move_type == 'out_invoice':
            # Determine revenue category from invoice lines
            revenue_category = self._determine_revenue_category()
            
            self.env['ams.financial.transaction'].create({
                'name': f"Invoice: {self.name}",
                'date': self.invoice_date or fields.Date.today(),
                'amount': self.amount_total,
                'transaction_type': 'income',
                'revenue_category_id': revenue_category.id if revenue_category else False,
                'partner_id': self.partner_id.id,
                'invoice_id': self.id,
                'chapter_id': self.chapter_id.id if self.chapter_id else False,
                'state': 'confirmed',
            })
    
    def _determine_revenue_category(self):
        """Auto-determine revenue category based on invoice content"""
        for line in self.invoice_line_ids:
            if line.product_id.is_membership:
                return self.env['ams.revenue.category'].search([
                    ('category_type', '=', 'membership')
                ], limit=1)
            # Add more logic for events, donations, etc.
        return False
