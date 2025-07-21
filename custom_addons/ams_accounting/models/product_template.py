from odoo import models, fields, api
from odoo.exceptions import ValidationError

class ProductTemplate(models.Model):
    _inherit = 'product.template'
    
    # Accounting configuration
    has_account_mapping = fields.Boolean('Has Account Mapping', compute='_compute_has_account_mapping', store=True)
    account_mapping_ids = fields.One2many('product.account.mapping', 'product_template_id', 'Account Mappings')
    account_mapping_count = fields.Integer('Account Mapping Count', compute='_compute_account_mapping_count')
    
    # Revenue accounting settings
    use_deferred_revenue = fields.Boolean('Use Deferred Revenue', default=False,
                                         help="Use deferred revenue accounting for this product")
    revenue_recognition_method = fields.Selection([
        ('immediate', 'Immediate Recognition'),
        ('deferred_monthly', 'Monthly Deferral'),
        ('deferred_quarterly', 'Quarterly Deferral'),
        ('deferred_yearly', 'Yearly Deferral'),
        ('custom', 'Custom Period')
    ], string='Revenue Recognition Method', default='immediate')
    
    deferral_period_months = fields.Integer('Deferral Period (Months)', default=12,
                                           help="Number of months to defer revenue recognition")
    
    # Default account assignments
    income_account_id = fields.Many2one('account.account', 'Income Account',
                                       domain="[('account_type', 'in', ['income', 'income_other']), ('company_id', '=', current_company_id)]",
                                       help="Default income account for this product")
    expense_account_id = fields.Many2one('account.account', 'Expense Account',
                                        domain="[('account_type', 'in', ['expense', 'expense_direct_cost']), ('company_id', '=', current_company_id)]",
                                        help="Default expense account for this product")
    deferred_revenue_account_id = fields.Many2one('account.account', 'Deferred Revenue Account',
                                                 domain="[('account_type', 'in', ['liability_current', 'liability_non_current']), ('company_id', '=', current_company_id)]",
                                                 help="Account for deferred revenue")
    
    # Financial statistics
    total_revenue_ytd = fields.Float('YTD Revenue', compute='_compute_revenue_stats', store=True,
                                    help="Year-to-date revenue from this product")
    total_subscriptions_sold = fields.Integer('Subscriptions Sold', compute='_compute_subscription_stats', store=True)
    active_subscriptions = fields.Integer('Active Subscriptions', compute='_compute_subscription_stats', store=True)
    
    # AMS-specific accounting
    ams_revenue_category = fields.Selection([
        ('membership', 'Membership Revenue'),
        ('chapter', 'Chapter Revenue'),
        ('publication', 'Publication Revenue'),
        ('merchandise', 'Merchandise Revenue'),
        ('services', 'Services Revenue'),
        ('other', 'Other Revenue')
    ], string='AMS Revenue Category', compute='_compute_ams_revenue_category', store=True)
    
    @api.depends('account_mapping_ids')
    def _compute_has_account_mapping(self):
        for product in self:
            product.has_account_mapping = bool(product.account_mapping_ids)
    
    @api.depends('account_mapping_ids')
    def _compute_account_mapping_count(self):
        for product in self:
            product.account_mapping_count = len(product.account_mapping_ids)
    
    @api.depends('is_subscription_product', 'subscription_type_id.code')
    def _compute_ams_revenue_category(self):
        for product in self:
            if product.is_subscription_product and product.subscription_type_id:
                code = product.subscription_type_id.code
                if code == 'membership':
                    product.ams_revenue_category = 'membership'
                elif code == 'chapter':
                    product.ams_revenue_category = 'chapter'
                elif code == 'publication':
                    product.ams_revenue_category = 'publication'
                else:
                    product.ams_revenue_category = 'other'
            elif product.type == 'service':
                product.ams_revenue_category = 'services'
            else:
                product.ams_revenue_category = 'merchandise'
    
    @api.depends('product_variant_ids.subscription_ids')
    def _compute_subscription_stats(self):
        for template in self:
            if template.is_subscription_product:
                all_subscriptions = template.product_variant_ids.mapped('subscription_ids')
                template.total_subscriptions_sold = len(all_subscriptions)
                template.active_subscriptions = len(all_subscriptions.filtered(lambda s: s.state == 'active'))
            else:
                template.total_subscriptions_sold = 0
                template.active_subscriptions = 0
    
    @api.depends('product_variant_ids')
    def _compute_revenue_stats(self):
        for template in self:
            current_year = fields.Date.today().year
            year_start = fields.Date.from_string(f'{current_year}-01-01')
            
            # Get revenue from account move lines
            move_lines = self.env['account.move.line'].search([
                ('product_id', 'in', template.product_variant_ids.ids),
                ('account_id.account_type', 'in', ['income', 'income_other']),
                ('date', '>=', year_start),
                ('move_id.state', '=', 'posted')
            ])
            
            template.total_revenue_ytd = sum(move_lines.mapped('credit')) - sum(move_lines.mapped('debit'))
    
    @api.onchange('is_subscription_product')
    def _onchange_is_subscription_product(self):
        """Set defaults when marking as subscription product"""
        super()._onchange_is_subscription_product()
        if self.is_subscription_product:
            self.use_deferred_revenue = True
            self.revenue_recognition_method = 'deferred_monthly'
        else:
            self.use_deferred_revenue = False
            self.revenue_recognition_method = 'immediate'
    
    @api.onchange('subscription_type_id')
    def _onchange_subscription_type_id(self):
        """Auto-configure accounting based on subscription type"""
        super()._onchange_subscription_type_id()
        if self.subscription_type_id:
            # Set revenue recognition method based on subscription type
            if self.subscription_type_id.code == 'membership':
                self.revenue_recognition_method = 'deferred_yearly'
                self.deferral_period_months = 12
            elif self.subscription_type_id.code == 'chapter':
                self.revenue_recognition_method = 'deferred_yearly'
                self.deferral_period_months = 12
            elif self.subscription_type_id.code == 'publication':
                self.revenue_recognition_method = 'deferred_monthly'
                self.deferral_period_months = 12
            
            # Auto-assign accounts if available
            self._auto_assign_accounts()
    
    def _auto_assign_accounts(self):
        """Auto-assign accounts based on AMS revenue category"""
        if not self.ams_revenue_category:
            return
            
        # Map revenue categories to AMS account types
        ams_account_mapping = {
            'membership': 'membership_revenue',
            'chapter': 'chapter_revenue',
            'publication': 'publication_revenue',
        }
        
        ams_account_type = ams_account_mapping.get(self.ams_revenue_category)
        if not ams_account_type:
            return
        
        # Find appropriate income account
        if not self.income_account_id:
            income_account = self.env['account.account'].search([
                ('ams_account_type', '=', ams_account_type),
                ('account_type', 'in', ['income', 'income_other']),
                ('company_id', '=', self.env.company.id)
            ], limit=1)
            if income_account:
                self.income_account_id = income_account.id
        
        # Find deferred revenue account if using deferred revenue
        if self.use_deferred_revenue and not self.deferred_revenue_account_id:
            deferred_account = self.env['account.account'].search([
                ('ams_account_type', '=', 'deferred_revenue'),
                ('account_type', 'in', ['liability_current', 'liability_non_current']),
                ('company_id', '=', self.env.company.id)
            ], limit=1)
            if deferred_account:
                self.deferred_revenue_account_id = deferred_account.id
    
    def action_configure_account_mapping(self):
        """Action to configure account mapping for this product"""
        # Check if mapping already exists
        existing_mapping = self.account_mapping_ids.filtered(
            lambda m: m.company_id == self.env.company
        )
        
        if existing_mapping:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Edit Account Mapping',
                'res_model': 'product.account.mapping',
                'view_mode': 'form',
                'res_id': existing_mapping[0].id,
                'target': 'new',
            }
        else:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Create Account Mapping',
                'res_model': 'product.account.mapping',
                'view_mode': 'form',
                'target': 'new',
                'context': {
                    'default_product_id': self.product_variant_id.id,
                    'default_is_subscription_mapping': self.is_subscription_product,
                    'default_subscription_type_id': self.subscription_type_id.id,
                    'default_income_account_id': self.income_account_id.id,
                    'default_expense_account_id': self.expense_account_id.id,
                    'default_deferred_revenue_account_id': self.deferred_revenue_account_id.id,
                    'default_use_deferred_revenue': self.use_deferred_revenue,
                    'default_deferral_period_months': self.deferral_period_months,
                }
            }
    
    def action_view_account_mappings(self):
        """View all account mappings for this product"""
        return {
            'type': 'ir.actions.act_window',
            'name': f'Account Mappings - {self.name}',
            'res_model': 'product.account.mapping',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', self.account_mapping_ids.ids)],
            'context': {'default_product_id': self.product_variant_id.id}
        }
    
    def action_create_default_mapping(self):
        """Create default account mapping for all companies"""
        for company in self.env['res.company'].search([]):
            existing = self.account_mapping_ids.filtered(lambda m: m.company_id == company)
            if not existing:
                mapping_vals = {
                    'product_id': self.product_variant_id.id,
                    'company_id': company.id,
                    'auto_create_entries': True,
                    'use_deferred_revenue': self.use_deferred_revenue,
                    'deferral_period_months': self.deferral_period_months,
                }
                
                # Try to find appropriate accounts for this company
                income_account = self.env['account.account'].search([
                    ('ams_account_type', '=', 'membership_revenue' if self.ams_revenue_category == 'membership' else 'other'),
                    ('account_type', 'in', ['income', 'income_other']),
                    ('company_id', '=', company.id)
                ], limit=1)
                
                if income_account:
                    mapping_vals['income_account_id'] = income_account.id
                
                self.env['product.account.mapping'].create(mapping_vals)
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Account Mappings Created',
                'message': f'Default account mappings have been created for product {self.name}.',
                'type': 'success',
            }
        }
    
    def action_view_revenue_analytics(self):
        """View revenue analytics for this product"""
        move_lines = self.env['account.move.line'].search([
            ('product_id', 'in', self.product_variant_ids.ids),
            ('account_id.account_type', 'in', ['income', 'income_other']),
            ('move_id.state', '=', 'posted')
        ])
        
        return {
            'type': 'ir.actions.act_window',
            'name': f'Revenue Analytics - {self.name}',
            'res_model': 'account.move.line',
            'view_mode': 'graph,pivot,tree,form',
            'domain': [('id', 'in', move_lines.ids)],
            'context': {
                'group_by': ['date:month', 'account_id'],
                'search_default_income': 1,
            }
        }
    
    def action_view_subscription_revenue(self):
        """View subscription revenue for this product"""
        if not self.is_subscription_product:
            return
            
        subscriptions = self.product_variant_ids.mapped('subscription_ids')
        
        return {
            'type': 'ir.actions.act_window',
            'name': f'Subscription Revenue - {self.name}',
            'res_model': 'ams.subscription',
            'view_mode': 'tree,form,graph,pivot',
            'domain': [('id', 'in', subscriptions.ids)],
            'context': {
                'group_by': ['state', 'subscription_type_id'],
                'search_default_active': 1,
            }
        }
    
    @api.constrains('deferral_period_months')
    def _check_deferral_period(self):
        for product in self:
            if product.use_deferred_revenue and product.deferral_period_months < 1:
                raise ValidationError("Deferral period must be at least 1 month when using deferred revenue.")
    
    @api.constrains('revenue_recognition_method', 'use_deferred_revenue')
    def _check_revenue_recognition_consistency(self):
        for product in self:
            if product.revenue_recognition_method != 'immediate' and not product.use_deferred_revenue:
                raise ValidationError("Deferred revenue must be enabled when using non-immediate revenue recognition methods.")

class ProductProduct(models.Model):
    _inherit = 'product.product'
    
    # Product variant specific accounting
    account_mapping_id = fields.Many2one('product.account.mapping', 'Account Mapping',
                                        compute='_compute_account_mapping')
    
    # Statistics for this specific variant
    variant_revenue_ytd = fields.Float('Variant YTD Revenue', compute='_compute_variant_revenue', store=True)
    variant_subscriptions_count = fields.Integer('Variant Subscriptions', compute='_compute_variant_subscriptions', store=True)
    
    def _compute_account_mapping(self):
        for product in self:
            mapping = self.env['product.account.mapping'].search([
                ('product_id', '=', product.id),
                ('company_id', '=', self.env.company.id)
            ], limit=1)
            product.account_mapping_id = mapping.id if mapping else False
    
    @api.depends('move_line_ids')
    def _compute_variant_revenue(self):
        for product in self:
            current_year = fields.Date.today().year
            year_start = fields.Date.from_string(f'{current_year}-01-01')
            
            revenue_lines = product.move_line_ids.filtered(
                lambda l: l.account_id.account_type in ['income', 'income_other'] and
                         l.date >= year_start and
                         l.move_id.state == 'posted'
            )
            
            product.variant_revenue_ytd = sum(revenue_lines.mapped('credit')) - sum(revenue_lines.mapped('debit'))
    
    @api.depends('subscription_ids')
    def _compute_variant_subscriptions(self):
        for product in self:
            if hasattr(product, 'subscription_ids'):
                product.variant_subscriptions_count = len(product.subscription_ids)
            else:
                product.variant_subscriptions_count = 0