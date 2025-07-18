# -*- coding: utf-8 -*-
#############################################################################
#
#    AMS Accounting - Account Account Model
#    Enhanced account model with AMS integration and cash flow mapping
#
#############################################################################

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class AccountAccount(models.Model):
    """
    Enhanced account model with AMS-specific features and cash flow mapping
    """
    _inherit = 'account.account'

    # AMS Integration Fields
    is_ams_subscription_account = fields.Boolean(
        'AMS Subscription Account',
        default=False,
        help="Mark this account for AMS subscription revenue tracking"
    )
    
    is_ams_chapter_account = fields.Boolean(
        'AMS Chapter Account',
        default=False,
        help="Mark this account for AMS chapter fee tracking"
    )
    
    is_ams_donation_account = fields.Boolean(
        'AMS Donation Account',
        default=False,
        help="Mark this account for AMS donation and grant tracking"
    )
    
    ams_subscription_type_ids = fields.Many2many(
        'ams.subscription.type',
        'account_subscription_type_rel',
        'account_id',
        'subscription_type_id',
        string='AMS Subscription Types',
        help="Link this account to specific subscription types"
    )
    
    ams_chapter_ids = fields.Many2many(
        'ams.chapter',
        'account_chapter_rel',
        'account_id',
        'chapter_id',
        string='AMS Chapters',
        help="Link this account to specific chapters"
    )

    # Cash Flow Integration
    cash_flow_type = fields.Many2one(
        'account.financial.report',
        string='Cash Flow Category',
        domain="[('parent_id.code', '=', 'CASH_FLOW')]",
        help="Map this account to a cash flow statement category"
    )
    
    cash_flow_sign = fields.Selection([
        ('positive', 'Positive (Inflow)'),
        ('negative', 'Negative (Outflow)'),
        ('auto', 'Automatic based on account type')
    ], string='Cash Flow Sign', default='auto',
    help="How this account should appear in cash flow calculations")

    # Analytics and Reporting
    enable_analytic_tracking = fields.Boolean(
        'Enable Analytic Tracking',
        default=False,
        help="Enable detailed analytic tracking for this account"
    )
    
    default_analytic_account_id = fields.Many2one(
        'account.analytic.account',
        string='Default Analytic Account',
        help="Default analytic account for entries in this account"
    )
    
    require_analytic = fields.Boolean(
        'Require Analytic Account',
        default=False,
        help="Require analytic account for all entries in this account"
    )

    # Budget Integration
    budget_control = fields.Boolean(
        'Budget Control',
        default=False,
        help="Enable budget control for this account"
    )
    
    budget_warning_level = fields.Float(
        'Budget Warning Level (%)',
        default=80.0,
        help="Warn when budget utilization reaches this percentage"
    )
    
    budget_block_level = fields.Float(
        'Budget Block Level (%)',
        default=100.0,
        help="Block transactions when budget utilization reaches this percentage"
    )

    # Financial Reporting Enhancements
    report_category = fields.Selection([
        ('revenue_membership', 'Membership Revenue'),
        ('revenue_chapter', 'Chapter Revenue'),
        ('revenue_publication', 'Publication Revenue'),
        ('revenue_event', 'Event Revenue'),
        ('revenue_donation', 'Donation Revenue'),
        ('revenue_grant', 'Grant Revenue'),
        ('expense_program', 'Program Expenses'),
        ('expense_admin', 'Administrative Expenses'),
        ('expense_fundraising', 'Fundraising Expenses'),
        ('asset_restricted', 'Restricted Assets'),
        ('asset_unrestricted', 'Unrestricted Assets'),
        ('liability_deferred', 'Deferred Revenue'),
        ('equity_net_assets', 'Net Assets'),
        ('other', 'Other')
    ], string='AMS Report Category',
    help="Categorize for AMS-specific financial reporting")

    # Multi-company/Chapter Support
    chapter_restriction = fields.Selection([
        ('none', 'No Restriction'),
        ('specific_chapters', 'Specific Chapters Only'),
        ('exclude_chapters', 'Exclude Specific Chapters')
    ], string='Chapter Restriction', default='none',
    help="Restrict account usage to specific chapters")
    
    allowed_chapter_ids = fields.Many2many(
        'ams.chapter',
        'account_allowed_chapter_rel',
        'account_id',
        'chapter_id',
        string='Allowed Chapters',
        help="Chapters allowed to use this account"
    )
    
    excluded_chapter_ids = fields.Many2many(
        'ams.chapter',
        'account_excluded_chapter_rel',
        'account_id',
        'chapter_id',
        string='Excluded Chapters',
        help="Chapters excluded from using this account"
    )

    # Computed Fields
    ams_subscription_revenue_ytd = fields.Float(
        'AMS Subscription Revenue YTD',
        compute='_compute_ams_revenue_ytd',
        store=False,
        help="Year-to-date AMS subscription revenue for this account"
    )
    
    ams_chapter_revenue_ytd = fields.Float(
        'AMS Chapter Revenue YTD',
        compute='_compute_ams_revenue_ytd',
        store=False,
        help="Year-to-date AMS chapter revenue for this account"
    )
    
    ams_transaction_count = fields.Integer(
        'AMS Transaction Count',
        compute='_compute_ams_stats',
        store=False,
        help="Number of AMS-related transactions this year"
    )

    @api.depends('move_line_ids', 'move_line_ids.ams_subscription_id', 'move_line_ids.ams_chapter_id')
    def _compute_ams_revenue_ytd(self):
        """Compute year-to-date AMS revenue for this account"""
        for account in self:
            # Get current year move lines
            current_year_lines = account.move_line_ids.filtered(
                lambda l: l.date.year == fields.Date.today().year and l.move_id.state == 'posted'
            )
            
            # Subscription revenue
            subscription_lines = current_year_lines.filtered(
                lambda l: l.move_id.is_ams_subscription_invoice
            )
            account.ams_subscription_revenue_ytd = sum(subscription_lines.mapped('credit')) - sum(subscription_lines.mapped('debit'))
            
            # Chapter revenue
            chapter_lines = current_year_lines.filtered(
                lambda l: l.move_id.ams_chapter_id
            )
            account.ams_chapter_revenue_ytd = sum(chapter_lines.mapped('credit')) - sum(chapter_lines.mapped('debit'))

    @api.depends('move_line_ids')
    def _compute_ams_stats(self):
        """Compute AMS transaction statistics"""
        for account in self:
            current_year_lines = account.move_line_ids.filtered(
                lambda l: l.date.year == fields.Date.today().year and l.move_id.state == 'posted'
            )
            
            ams_lines = current_year_lines.filtered(
                lambda l: l.move_id.is_ams_subscription_invoice or 
                         l.move_id.ams_subscription_id or 
                         l.move_id.ams_chapter_id
            )
            account.ams_transaction_count = len(ams_lines)

    @api.onchange('account_type')
    def _onchange_account_type(self):
        """Auto-set AMS-specific defaults based on account type"""
        super()._onchange_account_type()
        
        if self.account_type == 'income':
            self.cash_flow_sign = 'positive'
            self.enable_analytic_tracking = True
        elif self.account_type in ('expense', 'expense_depreciation', 'expense_direct_cost'):
            self.cash_flow_sign = 'negative'
            self.enable_analytic_tracking = True
        elif self.account_type in ('asset_cash', 'asset_current'):
            self.cash_flow_sign = 'auto'

    @api.onchange('is_ams_subscription_account')
    def _onchange_is_ams_subscription_account(self):
        """Set defaults for AMS subscription accounts"""
        if self.is_ams_subscription_account:
            self.report_category = 'revenue_membership'
            self.enable_analytic_tracking = True
            self.require_analytic = True

    @api.onchange('is_ams_chapter_account')
    def _onchange_is_ams_chapter_account(self):
        """Set defaults for AMS chapter accounts"""
        if self.is_ams_chapter_account:
            self.report_category = 'revenue_chapter'
            self.enable_analytic_tracking = True

    @api.onchange('is_ams_donation_account')
    def _onchange_is_ams_donation_account(self):
        """Set defaults for AMS donation accounts"""
        if self.is_ams_donation_account:
            self.report_category = 'revenue_donation'
            self.enable_analytic_tracking = True

    @api.constrains('budget_warning_level', 'budget_block_level')
    def _check_budget_levels(self):
        """Validate budget control levels"""
        for account in self:
            if account.budget_control:
                if account.budget_warning_level < 0 or account.budget_warning_level > 100:
                    raise UserError(_('Budget warning level must be between 0 and 100%'))
                if account.budget_block_level < 0 or account.budget_block_level > 100:
                    raise UserError(_('Budget block level must be between 0 and 100%'))
                if account.budget_warning_level > account.budget_block_level:
                    raise UserError(_('Budget warning level cannot be higher than block level'))

    @api.constrains('chapter_restriction', 'allowed_chapter_ids', 'excluded_chapter_ids')
    def _check_chapter_restrictions(self):
        """Validate chapter restriction configuration"""
        for account in self:
            if account.chapter_restriction == 'specific_chapters' and not account.allowed_chapter_ids:
                raise UserError(_('You must specify allowed chapters when using specific chapter restriction'))
            if account.chapter_restriction == 'exclude_chapters' and not account.excluded_chapter_ids:
                raise UserError(_('You must specify excluded chapters when using chapter exclusion restriction'))

    def get_cash_flow_amount(self, date_from, date_to, company_ids=None):
        """
        Calculate cash flow amount for this account in the given period
        """
        self.ensure_one()
        
        if not company_ids:
            company_ids = [self.env.company.id]
        
        domain = [
            ('account_id', '=', self.id),
            ('date', '>=', date_from),
            ('date', '<=', date_to),
            ('move_id.state', '=', 'posted'),
            ('company_id', 'in', company_ids)
        ]
        
        move_lines = self.env['account.move.line'].search(domain)
        
        # Calculate net amount (credit - debit for most accounts)
        net_amount = sum(move_lines.mapped('credit')) - sum(move_lines.mapped('debit'))
        
        # Apply cash flow sign rules
        if self.cash_flow_sign == 'negative':
            net_amount = -net_amount
        elif self.cash_flow_sign == 'auto':
            # Apply automatic sign based on account type
            if self.account_type in ('expense', 'expense_depreciation', 'expense_direct_cost'):
                net_amount = -net_amount
            elif self.account_type in ('asset_current', 'asset_non_current', 'asset_prepayments', 'asset_fixed'):
                net_amount = -net_amount  # Increase in assets is cash outflow
        
        return net_amount

    def action_view_ams_transactions(self):
        """Action to view AMS-related transactions for this account"""
        self.ensure_one()
        
        domain = [
            ('account_id', '=', self.id),
            '|', '|',
            ('move_id.is_ams_subscription_invoice', '=', True),
            ('move_id.ams_subscription_id', '!=', False),
            ('move_id.ams_chapter_id', '!=', False)
        ]
        
        return {
            'type': 'ir.actions.act_window',
            'name': f'AMS Transactions - {self.name}',
            'res_model': 'account.move.line',
            'view_mode': 'tree,form',
            'domain': domain,
            'context': {
                'search_default_group_by_move': 1,
                'search_default_posted': 1,
            }
        }

    def action_view_cash_flow_analysis(self):
        """Action to view cash flow analysis for this account"""
        self.ensure_one()
        
        return {
            'type': 'ir.actions.act_window',
            'name': f'Cash Flow Analysis - {self.name}',
            'res_model': 'account.move.line',
            'view_mode': 'graph,pivot,tree',
            'domain': [('account_id', '=', self.id)],
            'context': {
                'search_default_posted': 1,
                'group_by': ['date:month'],
                'graph_mode': 'line',
                'graph_measure': 'balance',
            }
        }

    def get_ams_revenue_breakdown(self, date_from=None, date_to=None):
        """
        Get detailed AMS revenue breakdown for this account
        """
        self.ensure_one()
        
        if not date_from:
            date_from = fields.Date.today().replace(month=1, day=1)  # Start of year
        if not date_to:
            date_to = fields.Date.today()
        
        domain = [
            ('account_id', '=', self.id),
            ('date', '>=', date_from),
            ('date', '<=', date_to),
            ('move_id.state', '=', 'posted'),
        ]
        
        move_lines = self.env['account.move.line'].search(domain)
        
        breakdown = {
            'total_revenue': 0.0,
            'subscription_revenue': 0.0,
            'chapter_revenue': 0.0,
            'renewal_revenue': 0.0,
            'other_revenue': 0.0,
            'transaction_count': len(move_lines),
        }
        
        for line in move_lines:
            amount = line.credit - line.debit
            breakdown['total_revenue'] += amount
            
            if line.move_id.is_ams_subscription_invoice:
                breakdown['subscription_revenue'] += amount
            elif line.move_id.is_ams_renewal_invoice:
                breakdown['renewal_revenue'] += amount
            elif line.move_id.ams_chapter_id:
                breakdown['chapter_revenue'] += amount
            else:
                breakdown['other_revenue'] += amount
        
        return breakdown

    @api.model
    def get_ams_accounts_summary(self):
        """
        Get summary of all AMS-related accounts
        """
        ams_accounts = self.search([
            '|', '|',
            ('is_ams_subscription_account', '=', True),
            ('is_ams_chapter_account', '=', True),
            ('is_ams_donation_account', '=', True)
        ])
        
        summary = []
        for account in ams_accounts:
            breakdown = account.get_ams_revenue_breakdown()
            summary.append({
                'account_id': account.id,
                'account_name': account.name,
                'account_code': account.code,
                'account_type': account.account_type,
                'is_subscription': account.is_ams_subscription_account,
                'is_chapter': account.is_ams_chapter_account,
                'is_donation': account.is_ams_donation_account,
                'breakdown': breakdown,
            })
        
        return summary