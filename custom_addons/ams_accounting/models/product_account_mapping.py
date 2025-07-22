from odoo import models, fields, api
from odoo.exceptions import ValidationError

class ProductAccountMapping(models.Model):
    _name = 'product.account.mapping'
    _description = 'Product to Account Mapping'
    _order = 'sequence, product_id'
    _rec_name = 'display_name'
    
    # Basic fields
    sequence = fields.Integer('Sequence', default=10)
    active = fields.Boolean('Active', default=True)
    
    # Product and account relationship
    product_id = fields.Many2one('product.product', 'Product', required=True, ondelete='cascade')
    product_template_id = fields.Many2one(related='product_id.product_tmpl_id', store=True, readonly=True)
    
    # Account mappings
    income_account_id = fields.Many2one('account.account', 'Income Account', 
                                       domain="[('account_type', 'in', ['income', 'income_other']), ('company_id', '=', company_id)]",
                                       help="Account for recording product revenue")
    
    expense_account_id = fields.Many2one('account.account', 'Expense Account',
                                        domain="[('account_type', 'in', ['expense', 'expense_direct_cost']), ('company_id', '=', company_id)]", 
                                        help="Account for recording product costs")
    
    receivable_account_id = fields.Many2one('account.account', 'Receivable Account',
                                           domain="[('account_type', '=', 'asset_receivable'), ('company_id', '=', company_id)]",
                                           help="Account for recording amounts due from customers")
    
    deferred_revenue_account_id = fields.Many2one('account.account', 'Deferred Revenue Account',
                                                 domain="[('account_type', 'in', ['liability_current', 'liability_non_current']), ('company_id', '=', company_id)]",
                                                 help="Account for deferred revenue (subscriptions paid in advance)")
    
    # Company and currency
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.company, required=True)
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id', readonly=True)
    
    # Subscription-specific settings
    is_subscription_mapping = fields.Boolean('Subscription Mapping', 
                                            related='product_id.is_subscription_product', 
                                            readonly=True, store=True)
    subscription_type_id = fields.Many2one('ams.subscription.type', 'Subscription Type',
                                          related='product_id.subscription_type_id',
                                          readonly=True, store=True)
    
    # Auto-mapping configuration
    auto_create_entries = fields.Boolean('Auto Create Entries', default=True,
                                        help="Automatically create accounting entries when this product is sold")
    
    use_deferred_revenue = fields.Boolean('Use Deferred Revenue', default=False,
                                         help="Use deferred revenue accounting for subscriptions")
    
    deferral_period_months = fields.Integer('Deferral Period (Months)', default=12,
                                           help="Number of months to defer revenue over")
    
    # Statistics and computed fields
    display_name = fields.Char('Display Name', compute='_compute_display_name', store=True)
    total_revenue_ytd = fields.Float('YTD Revenue', compute='_compute_revenue_stats', store=True)
    total_invoiced = fields.Float('Total Invoiced', compute='_compute_revenue_stats', store=True)
    
    @api.depends('product_id.name', 'income_account_id.name')
    def _compute_display_name(self):
        for mapping in self:
            if mapping.product_id and mapping.income_account_id:
                mapping.display_name = f"{mapping.product_id.name} → {mapping.income_account_id.name}"
            elif mapping.product_id:
                mapping.display_name = f"{mapping.product_id.name} → No Account"
            else:
                mapping.display_name = "No Product Selected"
    
    @api.depends()  # Remove the non-existent field dependency
    def _compute_revenue_stats(self):
        for mapping in self:
            if not mapping.income_account_id:
                mapping.total_revenue_ytd = 0.0
                mapping.total_invoiced = 0.0
                continue
            
        # Search for move lines related to this product instead of using non-existent relation
        product_lines = self.env['account.move.line'].search([
            ('account_id', '=', mapping.income_account_id.id),
            ('product_id', '=', mapping.product_id.id)
        ])
        
        # Calculate YTD revenue
        current_year = fields.Date.today().year
        year_start = fields.Date.from_string(f'{current_year}-01-01')
        ytd_lines = product_lines.filtered(lambda l: l.date >= year_start)
        
        mapping.total_revenue_ytd = sum(ytd_lines.mapped('credit')) - sum(ytd_lines.mapped('debit'))
        mapping.total_invoiced = sum(product_lines.mapped('credit')) - sum(product_lines.mapped('debit'))
    
    @api.model
    def create(self, vals):
        mapping = super().create(vals)
        # Auto-configure accounts based on subscription type
        if mapping.is_subscription_mapping and mapping.subscription_type_id:
            mapping._auto_configure_accounts()
        return mapping
    
    def write(self, vals):
        result = super().write(vals)
        # Re-configure accounts if subscription type changed
        if 'subscription_type_id' in vals:
            for mapping in self:
                if mapping.is_subscription_mapping:
                    mapping._auto_configure_accounts()
        return result
    
    def _auto_configure_accounts(self):
        """Auto-configure accounts based on subscription type"""
        if not self.subscription_type_id:
            return
            
        # Find appropriate accounts based on subscription type
        subscription_code = self.subscription_type_id.code
        
        # Map subscription types to AMS account types
        ams_type_mapping = {
            'membership': 'membership_revenue',
            'chapter': 'chapter_revenue', 
            'publication': 'publication_revenue'
        }
        
        ams_account_type = ams_type_mapping.get(subscription_code, 'other')
        
        # Find income account
        if not self.income_account_id:
            income_account = self.env['account.account'].search([
                ('ams_account_type', '=', ams_account_type),
                ('account_type', 'in', ['income', 'income_other']),
                ('company_id', '=', self.company_id.id)
            ], limit=1)
            
            if income_account:
                self.income_account_id = income_account.id
        
        # Find receivable account
        if not self.receivable_account_id:
            receivable_account = self.env['account.account'].search([
                ('ams_account_type', '=', 'subscription_receivable'),
                ('account_type', '=', 'asset_receivable'),
                ('company_id', '=', self.company_id.id)
            ], limit=1)
            
            if not receivable_account:
                # Fallback to default receivable account
                receivable_account = self.env['account.account'].search([
                    ('account_type', '=', 'asset_receivable'),
                    ('company_id', '=', self.company_id.id)
                ], limit=1)
            
            if receivable_account:
                self.receivable_account_id = receivable_account.id
        
        # Find deferred revenue account for recurring subscriptions
        if self.product_id.is_recurring and not self.deferred_revenue_account_id:
            deferred_account = self.env['account.account'].search([
                ('ams_account_type', '=', 'deferred_revenue'),
                ('account_type', 'in', ['liability_current', 'liability_non_current']),
                ('company_id', '=', self.company_id.id)
            ], limit=1)
            
            if deferred_account:
                self.deferred_revenue_account_id = deferred_account.id
                self.use_deferred_revenue = True
    
    def create_revenue_entry(self, amount, partner_id, invoice_id=None, subscription_id=None):
        """Create accounting entry for revenue recognition"""
        if not self.income_account_id or not self.receivable_account_id:
            raise ValidationError(f"Income and receivable accounts must be configured for product {self.product_id.name}")
        
        # Prepare journal entry
        move_vals = {
            'move_type': 'entry',
            'partner_id': partner_id,
            'ref': f"Revenue - {self.product_id.name}",
            'journal_id': self._get_revenue_journal().id,
            'company_id': self.company_id.id,
        }
        
        if invoice_id:
            move_vals['ref'] += f" (Invoice: {invoice_id})"
        
        # Create move lines
        line_vals = []
        
        if self.use_deferred_revenue and self.deferred_revenue_account_id:
            # Deferred revenue approach
            line_vals.extend([
                # Debit receivable
                {
                    'account_id': self.receivable_account_id.id,
                    'partner_id': partner_id,
                    'debit': amount,
                    'credit': 0.0,
                    'name': f"Revenue - {self.product_id.name}",
                    'product_id': self.product_id.id,
                    'ams_subscription_id': subscription_id,
                },
                # Credit deferred revenue
                {
                    'account_id': self.deferred_revenue_account_id.id,
                    'partner_id': partner_id,
                    'debit': 0.0,
                    'credit': amount,
                    'name': f"Deferred Revenue - {self.product_id.name}",
                    'product_id': self.product_id.id,
                    'ams_subscription_id': subscription_id,
                }
            ])
        else:
            # Direct revenue recognition
            line_vals.extend([
                # Debit receivable
                {
                    'account_id': self.receivable_account_id.id,
                    'partner_id': partner_id,
                    'debit': amount,
                    'credit': 0.0,
                    'name': f"Revenue - {self.product_id.name}",
                    'product_id': self.product_id.id,
                    'ams_subscription_id': subscription_id,
                },
                # Credit income
                {
                    'account_id': self.income_account_id.id,
                    'partner_id': partner_id,
                    'debit': 0.0,
                    'credit': amount,
                    'name': f"Revenue - {self.product_id.name}",
                    'product_id': self.product_id.id,
                    'ams_subscription_id': subscription_id,
                }
            ])
        
        move_vals['line_ids'] = [(0, 0, line) for line in line_vals]
        
        # Create and post the move
        move = self.env['account.move'].create(move_vals)
        move.action_post()
        
        return move
    
    def recognize_deferred_revenue(self, amount, subscription_id=None):
        """Move revenue from deferred to income account"""
        if not self.use_deferred_revenue or not self.deferred_revenue_account_id:
            return
            
        move_vals = {
            'move_type': 'entry',
            'ref': f"Revenue Recognition - {self.product_id.name}",
            'journal_id': self._get_revenue_journal().id,
            'company_id': self.company_id.id,
            'line_ids': [
                # Debit deferred revenue
                (0, 0, {
                    'account_id': self.deferred_revenue_account_id.id,
                    'debit': amount,
                    'credit': 0.0,
                    'name': f"Revenue Recognition - {self.product_id.name}",
                    'product_id': self.product_id.id,
                    'ams_subscription_id': subscription_id,
                }),
                # Credit income
                (0, 0, {
                    'account_id': self.income_account_id.id,
                    'debit': 0.0,
                    'credit': amount,
                    'name': f"Revenue Recognition - {self.product_id.name}",
                    'product_id': self.product_id.id,
                    'ams_subscription_id': subscription_id,
                })
            ]
        }
        
        move = self.env['account.move'].create(move_vals)
        move.action_post()
        
        return move
    
    def _get_revenue_journal(self):
        """Get the appropriate journal for revenue entries"""
        journal = self.env['account.journal'].search([
            ('type', '=', 'general'),
            ('company_id', '=', self.company_id.id)
        ], limit=1)
        
        if not journal:
            journal = self.env['account.journal'].search([
                ('company_id', '=', self.company_id.id)
            ], limit=1)
            
        return journal
    
    def action_view_account_moves(self):
        """View all account moves for this product"""
        moves = self.env['account.move.line'].search([
            ('product_id', '=', self.product_id.id),
            ('account_id', 'in', [
                self.income_account_id.id,
                self.expense_account_id.id,
                self.receivable_account_id.id,
                self.deferred_revenue_account_id.id
            ])
        ]).mapped('move_id')
        
        return {
            'type': 'ir.actions.act_window',
            'name': f'Account Moves - {self.product_id.name}',
            'res_model': 'account.move',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', moves.ids)],
            'context': {'default_product_id': self.product_id.id}
        }
    
    @api.constrains('product_id', 'company_id')
    def _check_unique_product(self):
        for mapping in self:
            duplicate = self.search([
                ('product_id', '=', mapping.product_id.id),
                ('company_id', '=', mapping.company_id.id),
                ('id', '!=', mapping.id)
            ])
            if duplicate:
                raise ValidationError(f"Product {mapping.product_id.name} already has an account mapping in this company.")
    
    @api.constrains('deferral_period_months')
    def _check_deferral_period(self):
        for mapping in self:
            if mapping.deferral_period_months < 1:
                raise ValidationError("Deferral period must be at least 1 month.")
    
    _sql_constraints = [
        ('product_company_unique', 'unique(product_id, company_id)', 
         'Product can only have one account mapping per company!'),
        ('deferral_period_positive', 'CHECK(deferral_period_months > 0)',
         'Deferral period must be positive!'),
    ]