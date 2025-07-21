from odoo import models, fields, api
from dateutil.relativedelta import relativedelta

class ResPartner(models.Model):
    _inherit = 'res.partner'
    
    # Financial summary fields
    ams_total_receivable = fields.Float('AMS Total Receivable', compute='_compute_ams_financials', store=True,
                                       help="Total amount receivable from AMS subscriptions")
    ams_total_revenue = fields.Float('AMS Total Revenue', compute='_compute_ams_financials', store=True,
                                    help="Total revenue generated from AMS subscriptions")
    ams_ytd_revenue = fields.Float('AMS YTD Revenue', compute='_compute_ams_financials', store=True,
                                  help="Year-to-date revenue from AMS subscriptions")
    ams_deferred_revenue = fields.Float('AMS Deferred Revenue', compute='_compute_ams_financials', store=True,
                                       help="Outstanding deferred revenue from subscriptions")
    
    # Subscription financial tracking
    membership_revenue_ytd = fields.Float('Membership Revenue YTD', compute='_compute_subscription_financials', store=True)
    chapter_revenue_ytd = fields.Float('Chapter Revenue YTD', compute='_compute_subscription_financials', store=True)
    publication_revenue_ytd = fields.Float('Publication Revenue YTD', compute='_compute_subscription_financials', store=True)
    
    # Payment tracking
    ams_payment_status = fields.Selection([
        ('current', 'Current'),
        ('overdue', 'Overdue'),
        ('delinquent', 'Delinquent'),
        ('suspended', 'Suspended')
    ], string='AMS Payment Status', compute='_compute_payment_status', store=True)
    
    days_overdue = fields.Integer('Days Overdue', compute='_compute_payment_status', store=True)
    overdue_amount = fields.Float('Overdue Amount', compute='_compute_payment_status', store=True)
    
    # Credit and collection settings
    ams_credit_limit = fields.Float('AMS Credit Limit', default=0.0,
                                   help="Credit limit for AMS subscriptions and purchases")
    credit_hold = fields.Boolean('Credit Hold', default=False,
                                help="Put customer on credit hold for new subscriptions")
    collection_notes = fields.Text('Collection Notes',
                                  help="Notes for accounts receivable and collections")
    
    # Account preferences
    preferred_payment_method = fields.Selection([
        ('cash', 'Cash'),
        ('check', 'Check'),
        ('credit_card', 'Credit Card'),
        ('bank_transfer', 'Bank Transfer'),
        ('auto_debit', 'Auto Debit')
    ], string='Preferred Payment Method')
    
    auto_invoice = fields.Boolean('Auto Invoice', default=True,
                                 help="Automatically create invoices for subscription renewals")
    invoice_delivery_method = fields.Selection([
        ('email', 'Email'),
        ('mail', 'Mail'),
        ('portal', 'Customer Portal'),
        ('both', 'Email and Mail')
    ], string='Invoice Delivery', default='email')
    
    # Related account move lines for detailed tracking
    ams_move_line_ids = fields.One2many('account.move.line', compute='_compute_ams_move_lines',
                                       string='AMS Account Move Lines')
    
    @api.depends('subscription_ids', 'subscription_ids.invoice_ids', 'subscription_ids.amount')
    def _compute_ams_financials(self):
        for partner in self:
            # Get all subscription-related invoices and move lines
            subscription_invoices = partner.subscription_ids.mapped('invoice_ids')
            
            # Calculate receivables from unpaid invoices
            unpaid_invoices = subscription_invoices.filtered(lambda inv: inv.payment_state != 'paid')
            partner.ams_total_receivable = sum(unpaid_invoices.mapped('amount_residual'))
            
            # Calculate total revenue from all subscription invoices
            paid_invoices = subscription_invoices.filtered(lambda inv: inv.payment_state == 'paid')
            partner.ams_total_revenue = sum(paid_invoices.mapped('amount_total'))
            
            # Calculate YTD revenue
            current_year = fields.Date.today().year
            year_start = fields.Date.from_string(f'{current_year}-01-01')
            ytd_invoices = subscription_invoices.filtered(
                lambda inv: inv.invoice_date and inv.invoice_date >= year_start and inv.payment_state == 'paid'
            )
            partner.ams_ytd_revenue = sum(ytd_invoices.mapped('amount_total'))
            
            # Calculate deferred revenue
            deferred_lines = self.env['account.move.line'].search([
                ('partner_id', '=', partner.id),
                ('account_id.ams_account_type', '=', 'deferred_revenue'),
                ('balance', '>', 0)
            ])
            partner.ams_deferred_revenue = sum(deferred_lines.mapped('balance'))
    
    @api.depends('subscription_ids', 'subscription_ids.subscription_code', 'subscription_ids.invoice_ids')
    def _compute_subscription_financials(self):
        for partner in self:
            current_year = fields.Date.today().year
            year_start = fields.Date.from_string(f'{current_year}-01-01')
            
            # Calculate revenue by subscription type
            membership_subs = partner.subscription_ids.filtered(lambda s: s.subscription_code == 'membership')
            chapter_subs = partner.subscription_ids.filtered(lambda s: s.subscription_code == 'chapter')
            publication_subs = partner.subscription_ids.filtered(lambda s: s.subscription_code == 'publication')
            
            # Membership revenue YTD
            membership_invoices = membership_subs.mapped('invoice_ids').filtered(
                lambda inv: inv.invoice_date and inv.invoice_date >= year_start and inv.payment_state == 'paid'
            )
            partner.membership_revenue_ytd = sum(membership_invoices.mapped('amount_total'))
            
            # Chapter revenue YTD
            chapter_invoices = chapter_subs.mapped('invoice_ids').filtered(
                lambda inv: inv.invoice_date and inv.invoice_date >= year_start and inv.payment_state == 'paid'
            )
            partner.chapter_revenue_ytd = sum(chapter_invoices.mapped('amount_total'))
            
            # Publication revenue YTD
            publication_invoices = publication_subs.mapped('invoice_ids').filtered(
                lambda inv: inv.invoice_date and inv.invoice_date >= year_start and inv.payment_state == 'paid'
            )
            partner.publication_revenue_ytd = sum(publication_invoices.mapped('amount_total'))
    
    @api.depends('subscription_ids', 'subscription_ids.invoice_ids', 'subscription_ids.invoice_ids.payment_state')
    def _compute_payment_status(self):
        for partner in self:
            today = fields.Date.today()
            
            # Get overdue invoices
            overdue_invoices = partner.subscription_ids.mapped('invoice_ids').filtered(
                lambda inv: inv.payment_state in ['not_paid', 'partial'] and 
                           inv.invoice_date_due and 
                           inv.invoice_date_due < today
            )
            
            if not overdue_invoices:
                partner.ams_payment_status = 'current'
                partner.days_overdue = 0
                partner.overdue_amount = 0.0
            else:
                # Calculate days overdue (oldest invoice)
                oldest_due_date = min(overdue_invoices.mapped('invoice_date_due'))
                partner.days_overdue = (today - oldest_due_date).days
                partner.overdue_amount = sum(overdue_invoices.mapped('amount_residual'))
                
                # Determine status based on days overdue
                if partner.days_overdue <= 30:
                    partner.ams_payment_status = 'overdue'
                elif partner.days_overdue <= 90:
                    partner.ams_payment_status = 'delinquent'
                else:
                    partner.ams_payment_status = 'suspended'
    
    def _compute_ams_move_lines(self):
        for partner in self:
            # Get all move lines related to AMS subscriptions
            partner.ams_move_line_ids = self.env['account.move.line'].search([
                ('partner_id', '=', partner.id),
                ('ams_subscription_id', '!=', False)
            ])
    
    def action_view_ams_invoices(self):
        """View all AMS-related invoices for this partner"""
        invoices = self.subscription_ids.mapped('invoice_ids')
        return {
            'type': 'ir.actions.act_window',
            'name': f'AMS Invoices - {self.name}',
            'res_model': 'account.move',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', invoices.ids)],
            'context': {
                'default_partner_id': self.id,
                'search_default_subscription_invoices': 1
            }
        }
    
    def action_view_ams_payments(self):
        """View all AMS-related payments for this partner"""
        invoices = self.subscription_ids.mapped('invoice_ids')
        payments = invoices.mapped('payment_ids')
        return {
            'type': 'ir.actions.act_window',
            'name': f'AMS Payments - {self.name}',
            'res_model': 'account.payment',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', payments.ids)],
            'context': {
                'default_partner_id': self.id,
                'default_partner_type': 'customer'
            }
        }
    
    def action_view_ams_account_moves(self):
        """View all AMS-related account moves for this partner"""
        return {
            'type': 'ir.actions.act_window',
            'name': f'AMS Account Moves - {self.name}',
            'res_model': 'account.move.line',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', self.ams_move_line_ids.ids)],
            'context': {
                'default_partner_id': self.id,
                'search_default_ams_subscription': 1
            }
        }
    
    def action_create_payment(self):
        """Create a payment for outstanding AMS invoices"""
        if self.ams_total_receivable <= 0:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'No Outstanding Amount',
                    'message': 'This customer has no outstanding AMS receivables.',
                    'type': 'info',
                }
            }
        
        return {
            'type': 'ir.actions.act_window',
            'name': 'Register Payment',
            'res_model': 'account.payment.register',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_partner_id': self.id,
                'default_amount': self.ams_total_receivable,
                'default_partner_type': 'customer',
                'default_payment_type': 'inbound',
            }
        }
    
    def action_ams_statement_of_account(self):
        """Generate AMS statement of account"""
        return {
            'type': 'ir.actions.act_window',
            'name': f'AMS Statement - {self.name}',
            'res_model': 'ams.account.statement.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_partner_id': self.id,
                'default_date_from': fields.Date.today() - relativedelta(months=12),
                'default_date_to': fields.Date.today(),
            }
        }
    
    def action_toggle_credit_hold(self):
        """Toggle credit hold status"""
        self.credit_hold = not self.credit_hold
        status = "activated" if self.credit_hold else "removed"
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': f'Credit Hold {status.title()}',
                'message': f'Credit hold has been {status} for {self.name}.',
                'type': 'warning' if self.credit_hold else 'success',
            }
        }
    
    def check_credit_limit(self, additional_amount=0.0):
        """Check if customer is within credit limit"""
        if self.ams_credit_limit <= 0:  # No limit set
            return True
            
        total_exposure = self.ams_total_receivable + additional_amount
        return total_exposure <= self.ams_credit_limit
    
    def get_available_credit(self):
        """Get available credit amount"""
        if self.ams_credit_limit <= 0:
            return float('inf')  # Unlimited
        return max(0, self.ams_credit_limit - self.ams_total_receivable)
    
    def _get_ams_financial_summary(self):
        """Get comprehensive financial summary for reports"""
        return {
            'partner_name': self.name,
            'total_receivable': self.ams_total_receivable,
            'total_revenue': self.ams_total_revenue,
            'ytd_revenue': self.ams_ytd_revenue,
            'deferred_revenue': self.ams_deferred_revenue,
            'membership_revenue_ytd': self.membership_revenue_ytd,
            'chapter_revenue_ytd': self.chapter_revenue_ytd,
            'publication_revenue_ytd': self.publication_revenue_ytd,
            'payment_status': self.ams_payment_status,
            'days_overdue': self.days_overdue,
            'overdue_amount': self.overdue_amount,
            'credit_limit': self.ams_credit_limit,
            'available_credit': self.get_available_credit(),
            'credit_hold': self.credit_hold,
        }

class AMSAccountStatementWizard(models.TransientModel):
    _name = 'ams.account.statement.wizard'
    _description = 'AMS Account Statement Generator'
    
    partner_id = fields.Many2one('res.partner', 'Customer', required=True)
    date_from = fields.Date('From Date', required=True, default=lambda self: fields.Date.today() - relativedelta(months=12))
    date_to = fields.Date('To Date', required=True, default=fields.Date.today)
    include_paid = fields.Boolean('Include Paid Invoices', default=True)
    include_draft = fields.Boolean('Include Draft Invoices', default=False)
    
    def action_generate_statement(self):
        """Generate and download statement"""
        # This would typically generate a PDF report
        # For now, return a tree view of relevant transactions
        
        domain = [
            ('partner_id', '=', self.partner_id.id),
            ('ams_subscription_id', '!=', False),
            ('date', '>=', self.date_from),
            ('date', '<=', self.date_to),
        ]
        
        if not self.include_draft:
            domain.append(('move_id.state', '=', 'posted'))
        
        return {
            'type': 'ir.actions.act_window',
            'name': f'AMS Statement - {self.partner_id.name}',
            'res_model': 'account.move.line',
            'view_mode': 'tree,form',
            'domain': domain,
            'context': {
                'default_partner_id': self.partner_id.id,
                'search_default_ams_subscription': 1,
            }
        }