from odoo import models, fields, api
from odoo.exceptions import ValidationError

class AccountMove(models.Model):
    _inherit = 'account.move'
    
    # AMS-specific fields
    ams_subscription_id = fields.Many2one('ams.subscription', 'AMS Subscription',
                                         help="Link to AMS subscription for revenue tracking")
    is_ams_transaction = fields.Boolean('AMS Transaction', compute='_compute_is_ams_transaction', store=True,
                                       help="True if this move contains AMS-related transactions")
    ams_transaction_type = fields.Selection([
        ('subscription_invoice', 'Subscription Invoice'),
        ('renewal_invoice', 'Renewal Invoice'),
        ('revenue_recognition', 'Revenue Recognition'),
        ('deferred_revenue', 'Deferred Revenue'),
        ('refund', 'Refund'),
        ('adjustment', 'Adjustment'),
        ('other', 'Other AMS Transaction')
    ], string='AMS Transaction Type', compute='_compute_ams_transaction_type', store=True)
    
    # Revenue tracking
    ams_revenue_amount = fields.Float('AMS Revenue Amount', compute='_compute_ams_amounts', store=True,
                                     help="Total AMS revenue in this move")
    ams_deferred_amount = fields.Float('AMS Deferred Amount', compute='_compute_ams_amounts', store=True,
                                      help="Total AMS deferred revenue in this move")
    
    # Subscription details
    subscription_type_code = fields.Selection(related='ams_subscription_id.subscription_code', store=True, readonly=True)
    subscription_partner_id = fields.Many2one(related='ams_subscription_id.partner_id', store=True, readonly=True)
    
    @api.depends('line_ids.ams_subscription_id')
    def _compute_is_ams_transaction(self):
        for move in self:
            move.is_ams_transaction = any(line.ams_subscription_id for line in move.line_ids)
    
    @api.depends('is_ams_transaction', 'is_renewal_invoice', 'line_ids.account_id.ams_account_type')
    def _compute_ams_transaction_type(self):
        for move in self:
            if not move.is_ams_transaction:
                move.ams_transaction_type = False
                continue
                
            # Determine transaction type
            if move.move_type in ['out_invoice', 'out_refund']:
                if hasattr(move, 'is_renewal_invoice') and move.is_renewal_invoice:
                    move.ams_transaction_type = 'renewal_invoice'
                else:
                    move.ams_transaction_type = 'subscription_invoice'
            elif move.move_type == 'entry':
                # Check account types in move lines
                ams_account_types = move.line_ids.mapped('account_id.ams_account_type')
                if 'deferred_revenue' in ams_account_types:
                    move.ams_transaction_type = 'revenue_recognition'
                else:
                    move.ams_transaction_type = 'adjustment'
            else:
                move.ams_transaction_type = 'other'
    
    @api.depends('line_ids.credit', 'line_ids.debit', 'line_ids.account_id.ams_account_type')
    def _compute_ams_amounts(self):
        for move in self:
            revenue_amount = 0.0
            deferred_amount = 0.0
            
            for line in move.line_ids:
                if line.account_id.ams_account_type:
                    if line.account_id.ams_account_type in ['membership_revenue', 'chapter_revenue', 'publication_revenue']:
                        revenue_amount += line.credit - line.debit
                    elif line.account_id.ams_account_type == 'deferred_revenue':
                        deferred_amount += line.credit - line.debit
            
            move.ams_revenue_amount = revenue_amount
            move.ams_deferred_amount = deferred_amount
    
    def action_post(self):
        """Override to update subscription accounting when posting"""
        result = super().action_post()
        
        # Update subscription financial totals
        for move in self:
            if move.ams_subscription_id:
                move.ams_subscription_id._compute_financial_totals()
                
        return result
    
    def button_cancel(self):
        """Override to handle AMS-specific cancellation logic"""
        # Check for processed revenue recognitions
        for move in self:
            revenue_recognitions = self.env['ams.revenue.recognition'].search([
                ('move_id', '=', move.id),
                ('state', '=', 'processed')
            ])
            if revenue_recognitions:
                raise ValidationError(
                    "Cannot cancel this move because it contains processed revenue recognition entries. "
                    "Please cancel the revenue recognition entries first."
                )
        
        result = super().button_cancel()
        
        # Update subscription financial totals
        for move in self:
            if move.ams_subscription_id:
                move.ams_subscription_id._compute_financial_totals()
                
        return result

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'
    
    # AMS-specific fields
    ams_subscription_id = fields.Many2one('ams.subscription', 'AMS Subscription',
                                         help="Link to AMS subscription for detailed tracking")
    is_ams_line = fields.Boolean('AMS Line', compute='_compute_is_ams_line', store=True,
                                help="True if this line is related to AMS")
    
    # Subscription details for reporting
    subscription_type_code = fields.Selection(related='ams_subscription_id.subscription_code', store=True, readonly=True)
    subscription_type_id = fields.Many2one(related='ams_subscription_id.subscription_type_id', store=True, readonly=True)
    subscription_partner_id = fields.Many2one(related='ams_subscription_id.partner_id', store=True, readonly=True)
    chapter_id = fields.Many2one(related='ams_subscription_id.chapter_id', store=True, readonly=True)
    
    # Revenue recognition tracking
    revenue_recognition_id = fields.Many2one('ams.revenue.recognition', 'Revenue Recognition',
                                            help="Link to revenue recognition entry if applicable")
    is_deferred_revenue = fields.Boolean('Deferred Revenue', compute='_compute_is_deferred_revenue', store=True)
    
    # Financial categorization
    ams_line_type = fields.Selection([
        ('subscription_revenue', 'Subscription Revenue'),
        ('deferred_revenue', 'Deferred Revenue'),
        ('revenue_recognition', 'Revenue Recognition'),
        ('subscription_receivable', 'Subscription Receivable'),
        ('refund', 'Refund'),
        ('adjustment', 'Adjustment')
    ], string='AMS Line Type', compute='_compute_ams_line_type', store=True)
    
    @api.depends('ams_subscription_id', 'account_id.is_ams_account')
    def _compute_is_ams_line(self):
        for line in self:
            line.is_ams_line = bool(line.ams_subscription_id or line.account_id.is_ams_account)
    
    @api.depends('account_id.ams_account_type')
    def _compute_is_deferred_revenue(self):
        for line in self:
            line.is_deferred_revenue = line.account_id.ams_account_type == 'deferred_revenue'
    
    @api.depends('account_id.ams_account_type', 'revenue_recognition_id', 'move_id.move_type')
    def _compute_ams_line_type(self):
        for line in self:
            if not line.is_ams_line:
                line.ams_line_type = False
                continue
                
            if line.revenue_recognition_id:
                line.ams_line_type = 'revenue_recognition'
            elif line.account_id.ams_account_type == 'deferred_revenue':
                line.ams_line_type = 'deferred_revenue'
            elif line.account_id.ams_account_type in ['membership_revenue', 'chapter_revenue', 'publication_revenue']:
                line.ams_line_type = 'subscription_revenue'
            elif line.account_id.ams_account_type == 'subscription_receivable':
                line.ams_line_type = 'subscription_receivable'
            elif line.move_id.move_type == 'out_refund':
                line.ams_line_type = 'refund'
            else:
                line.ams_line_type = 'adjustment'
    
    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        """Override read_group to enable grouping by AMS fields"""
        # Add AMS-specific group by options
        if 'subscription_type_code' in groupby:
            self = self.with_context(group_by_no_leaf=True)
        if 'ams_line_type' in groupby:
            self = self.with_context(group_by_no_leaf=True)
            
        return super().read_group(domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)

class AccountPayment(models.Model):
    _inherit = 'account.payment'
    
    # AMS payment tracking
    ams_subscription_ids = fields.Many2many('ams.subscription', 
                                           compute='_compute_ams_subscriptions', store=True,
                                           string='Related AMS Subscriptions')
    is_ams_payment = fields.Boolean('AMS Payment', compute='_compute_ams_subscriptions', store=True)
    ams_payment_count = fields.Integer('AMS Subscription Count', compute='_compute_ams_subscriptions', store=True)
    
    @api.depends('reconciled_invoice_ids.ams_subscription_id')
    def _compute_ams_subscriptions(self):
        for payment in self:
            subscription_ids = payment.reconciled_invoice_ids.mapped('ams_subscription_id')
            payment.ams_subscription_ids = [(6, 0, subscription_ids.ids)]
            payment.is_ams_payment = bool(subscription_ids)
            payment.ams_payment_count = len(subscription_ids)
    
    def action_view_ams_subscriptions(self):
        """View related AMS subscriptions"""
        if not self.ams_subscription_ids:
            return
            
        return {
            'type': 'ir.actions.act_window',
            'name': 'Related AMS Subscriptions',
            'res_model': 'ams.subscription',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', self.ams_subscription_ids.ids)],
            'context': {}
        }

class AccountJournal(models.Model):
    _inherit = 'account.journal'
    
    # AMS journal configuration
    is_ams_journal = fields.Boolean('AMS Journal', default=False,
                                   help="Mark this journal for AMS-specific transactions")
    ams_journal_type = fields.Selection([
        ('subscription', 'Subscription Revenue'),
        ('renewal', 'Renewal Revenue'),
        ('recognition', 'Revenue Recognition'),
        ('adjustment', 'AMS Adjustments')
    ], string='AMS Journal Type', help="Type of AMS transactions for this journal")
    
    # Default accounts for AMS transactions
    default_ams_income_account_id = fields.Many2one('account.account', 'Default AMS Income Account',
                                                   domain="[('account_type', 'in', ['income', 'income_other']), ('company_id', '=', company_id)]")
    default_ams_receivable_account_id = fields.Many2one('account.account', 'Default AMS Receivable Account',
                                                       domain="[('account_type', '=', 'asset_receivable'), ('company_id', '=', company_id)]")
    default_ams_deferred_account_id = fields.Many2one('account.account', 'Default AMS Deferred Revenue Account',
                                                     domain="[('account_type', 'in', ['liability_current', 'liability_non_current']), ('company_id', '=', company_id)]")

class AccountAnalyticLine(models.Model):
    _inherit = 'account.analytic.line'
    
    # AMS analytic tracking
    ams_subscription_id = fields.Many2one('ams.subscription', 'AMS Subscription',
                                         help="Link analytic entries to AMS subscriptions")
    subscription_type_code = fields.Selection(related='ams_subscription_id.subscription_code', store=True, readonly=True)
    chapter_id = fields.Many2one(related='ams_subscription_id.chapter_id', store=True, readonly=True)