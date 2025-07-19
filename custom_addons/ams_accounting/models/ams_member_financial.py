from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import logging

_logger = logging.getLogger(__name__)


class AMSMemberFinancial(models.Model):
    """
    Enhanced partner model with comprehensive AMS financial tracking
    """
    _inherit = 'res.partner'
    
    # Financial Summary Fields
    total_ams_revenue = fields.Float('Total AMS Revenue', compute='_compute_ams_financial_summary', store=True,
        help="Total revenue generated from this member across all subscriptions")
    
    current_year_revenue = fields.Float('Current Year Revenue', compute='_compute_ams_financial_summary', store=True)
    last_year_revenue = fields.Float('Last Year Revenue', compute='_compute_ams_financial_summary', store=True)
    
    total_ams_payments = fields.Float('Total AMS Payments', compute='_compute_ams_financial_summary', store=True)
    outstanding_ams_balance = fields.Float('Outstanding AMS Balance', compute='_compute_ams_financial_summary', store=True)
    
    # Member Value Metrics
    customer_lifetime_value = fields.Float('Customer Lifetime Value', compute='_compute_member_value_metrics', store=True)
    monthly_recurring_revenue = fields.Float('Member MRR', compute='_compute_member_value_metrics', store=True)
    annual_recurring_revenue = fields.Float('Member ARR', compute='_compute_member_value_metrics', store=True)
    
    # Payment Behavior Analysis
    average_payment_delay = fields.Float('Avg Payment Delay (Days)', compute='_compute_payment_behavior', store=True)
    payment_reliability_score = fields.Float('Payment Reliability Score', compute='_compute_payment_behavior', store=True,
        help="Score from 0-100 based on payment history")
    
    payment_risk_level = fields.Selection([
        ('low', 'Low Risk'),
        ('medium', 'Medium Risk'),
        ('high', 'High Risk'),
        ('critical', 'Critical Risk')
    ], string='Payment Risk Level', compute='_compute_payment_behavior', store=True)
    
    # Financial Status
    is_financial_member = fields.Boolean('Financial Member', compute='_compute_financial_status', store=True,
        help="Member has paid all outstanding balances")
    
    has_payment_plan = fields.Boolean('Has Payment Plan', default=False)
    payment_plan_id = fields.Many2one('ams.payment.plan', 'Payment Plan')
    
    # Credit Management
    ams_credit_limit = fields.Float('AMS Credit Limit', default=0.0)
    ams_credit_used = fields.Float('AMS Credit Used', compute='_compute_credit_usage', store=True)
    ams_credit_available = fields.Float('AMS Credit Available', compute='_compute_credit_usage', store=True)
    
    # Membership Financial History
    membership_start_year = fields.Integer('Membership Start Year', compute='_compute_membership_history', store=True)
    years_as_member = fields.Float('Years as Member', compute='_compute_membership_history', store=True)
    membership_gap_years = fields.Integer('Years with Gaps', compute='_compute_membership_history', store=True)
    
    # Invoice Analytics
    total_ams_invoices = fields.Integer('Total AMS Invoices', compute='_compute_invoice_analytics', store=True)
    paid_invoices_count = fields.Integer('Paid Invoices', compute='_compute_invoice_analytics', store=True)
    overdue_invoices_count = fields.Integer('Overdue Invoices', compute='_compute_invoice_analytics', store=True)
    
    # Communication Preferences for Financial Matters
    financial_communication_method = fields.Selection([
        ('email', 'Email'),
        ('mail', 'Postal Mail'),
        ('phone', 'Phone'),
        ('portal', 'Member Portal')
    ], string='Financial Communication Method', default='email')
    
    suppress_financial_emails = fields.Boolean('Suppress Financial Emails', default=False)
    
    @api.depends('subscription_ids', 'subscription_ids.total_invoiced', 'subscription_ids.total_paid', 'subscription_ids.outstanding_balance')
    def _compute_ams_financial_summary(self):
        for partner in self:
            subscriptions = partner.subscription_ids
            
            # Total revenue and payments
            partner.total_ams_revenue = sum(subscriptions.mapped('total_invoiced'))
            partner.total_ams_payments = sum(subscriptions.mapped('total_paid'))
            partner.outstanding_ams_balance = sum(subscriptions.mapped('outstanding_balance'))
            
            # Year-specific calculations
            current_year = fields.Date.today().year
            current_year_start = fields.Date(current_year, 1, 1)
            last_year_start = fields.Date(current_year - 1, 1, 1)
            last_year_end = fields.Date(current_year - 1, 12, 31)
            
            # Current year revenue
            current_year_invoices = partner.invoice_ids.filtered(
                lambda inv: inv.invoice_date >= current_year_start and 
                           inv.state == 'posted' and 
                           inv.subscription_id
            )
            partner.current_year_revenue = sum(current_year_invoices.mapped('amount_total'))
            
            # Last year revenue
            last_year_invoices = partner.invoice_ids.filtered(
                lambda inv: inv.invoice_date >= last_year_start and 
                           inv.invoice_date <= last_year_end and 
                           inv.state == 'posted' and 
                           inv.subscription_id
            )
            partner.last_year_revenue = sum(last_year_invoices.mapped('amount_total'))
    
    @api.depends('subscription_ids', 'subscription_ids.monthly_recurring_revenue', 'subscription_ids.annual_recurring_revenue', 'subscription_ids.lifetime_value')
    def _compute_member_value_metrics(self):
        for partner in self:
            active_subscriptions = partner.subscription_ids.filtered(lambda s: s.state == 'active')
            
            partner.monthly_recurring_revenue = sum(active_subscriptions.mapped('monthly_recurring_revenue'))
            partner.annual_recurring_revenue = sum(active_subscriptions.mapped('annual_recurring_revenue'))
            partner.customer_lifetime_value = sum(partner.subscription_ids.mapped('lifetime_value'))
    
    @api.depends('invoice_ids', 'invoice_ids.payment_date', 'invoice_ids.invoice_date_due', 'invoice_ids.payment_state')
    def _compute_payment_behavior(self):
        for partner in self:
            ams_invoices = partner.invoice_ids.filtered(
                lambda inv: inv.subscription_id and inv.state == 'posted'
            )
            
            if not ams_invoices:
                partner.average_payment_delay = 0.0
                partner.payment_reliability_score = 100.0
                partner.payment_risk_level = 'low'
                continue
            
            # Calculate average payment delay
            paid_invoices = ams_invoices.filtered(lambda inv: inv.payment_state == 'paid' and inv.payment_date)
            
            if paid_invoices:
                total_delay = 0
                for invoice in paid_invoices:
                    if invoice.invoice_date_due:
                        delay = (invoice.payment_date - invoice.invoice_date_due).days
                        total_delay += max(0, delay)  # Only count positive delays
                
                partner.average_payment_delay = total_delay / len(paid_invoices)
            else:
                partner.average_payment_delay = 0.0
            
            # Calculate payment reliability score
            total_invoices = len(ams_invoices)
            paid_on_time = len(paid_invoices.filtered(
                lambda inv: not inv.invoice_date_due or 
                           (inv.payment_date and inv.payment_date <= inv.invoice_date_due)
            ))
            overdue_invoices = len(ams_invoices.filtered(
                lambda inv: inv.invoice_date_due and 
                           inv.invoice_date_due < fields.Date.today() and 
                           inv.payment_state in ['not_paid', 'partial']
            ))
            
            # Base score on payment history
            if total_invoices > 0:
                on_time_ratio = paid_on_time / total_invoices
                base_score = on_time_ratio * 100
                
                # Penalties for current overdue invoices
                overdue_penalty = min(50, overdue_invoices * 10)
                
                # Penalty for average payment delay
                delay_penalty = min(30, partner.average_payment_delay * 2)
                
                partner.payment_reliability_score = max(0, base_score - overdue_penalty - delay_penalty)
            else:
                partner.payment_reliability_score = 100.0
            
            # Determine risk level
            if partner.payment_reliability_score >= 80:
                partner.payment_risk_level = 'low'
            elif partner.payment_reliability_score >= 60:
                partner.payment_risk_level = 'medium'
            elif partner.payment_reliability_score >= 40:
                partner.payment_risk_level = 'high'
            else:
                partner.payment_risk_level = 'critical'
    
    @api.depends('outstanding_ams_balance', 'total_ams_payments')
    def _compute_financial_status(self):
        for partner in self:
            partner.is_financial_member = (partner.outstanding_ams_balance <= 0.01)  # Allow for rounding
    
    @api.depends('ams_credit_limit', 'outstanding_ams_balance')
    def _compute_credit_usage(self):
        for partner in self:
            partner.ams_credit_used = partner.outstanding_ams_balance
            partner.ams_credit_available = max(0, partner.ams_credit_limit - partner.ams_credit_used)
    
    @api.depends('subscription_ids', 'subscription_ids.start_date', 'subscription_ids.state')
    def _compute_membership_history(self):
        for partner in self:
            membership_subscriptions = partner.subscription_ids.filtered(
                lambda s: s.subscription_code == 'membership'
            ).sorted('start_date')
            
            if not membership_subscriptions:
                partner.membership_start_year = 0
                partner.years_as_member = 0.0
                partner.membership_gap_years = 0
                continue
            
            # First membership year
            first_membership = membership_subscriptions[0]
            partner.membership_start_year = first_membership.start_date.year
            
            # Calculate years as member
            today = fields.Date.today()
            partner.years_as_member = (today - first_membership.start_date).days / 365.25
            
            # Calculate gap years (simplified - years without active membership)
            active_years = set()
            for subscription in membership_subscriptions.filtered(lambda s: s.state in ['active', 'expired']):
                start_year = subscription.start_date.year
                end_year = subscription.end_date.year if subscription.end_date else today.year
                
                for year in range(start_year, end_year + 1):
                    active_years.add(year)
            
            total_possible_years = today.year - partner.membership_start_year + 1
            partner.membership_gap_years = total_possible_years - len(active_years)
    
    @api.depends('invoice_ids', 'invoice_ids.subscription_id', 'invoice_ids.state', 'invoice_ids.payment_state')
    def _compute_invoice_analytics(self):
        for partner in self:
            ams_invoices = partner.invoice_ids.filtered(lambda inv: inv.subscription_id)
            
            partner.total_ams_invoices = len(ams_invoices)
            partner.paid_invoices_count = len(ams_invoices.filtered(lambda inv: inv.payment_state == 'paid'))
            
            # Overdue invoices
            today = fields.Date.today()
            overdue_invoices = ams_invoices.filtered(
                lambda inv: inv.invoice_date_due and 
                           inv.invoice_date_due < today and 
                           inv.payment_state in ['not_paid', 'partial'] and
                           inv.state == 'posted'
            )
            partner.overdue_invoices_count = len(overdue_invoices)
    
    def action_create_payment_plan(self):
        """Create a payment plan for this member"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Create Payment Plan',
            'res_model': 'ams.payment.plan',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_partner_id': self.id,
                'default_total_amount': self.outstanding_ams_balance,
            }
        }
    
    def action_view_financial_timeline(self):
        """View financial timeline for this member"""
        return {
            'type': 'ir.actions.act_window',
            'name': f'Financial Timeline - {self.name}',
            'res_model': 'ams.member.financial.timeline',
            'view_mode': 'tree,form',
            'domain': [('partner_id', '=', self.id)],
            'context': {
                'default_partner_id': self.id,
            }
        }
    
    def action_send_financial_statement(self):
        """Send financial statement to member"""
        if self.suppress_financial_emails:
            raise UserError(_('Financial emails are suppressed for this member.'))
        
        template = self.env.ref('ams_accounting.email_template_financial_statement', False)
        if not template:
            raise UserError(_('Financial statement email template not found.'))
        
        template.send_mail(self.id, force_send=True)
        
        # Log the action
        self.message_post(
            body=_('Financial statement sent via email.'),
            subject=_('Financial Statement Sent')
        )
    
    def action_generate_financial_report(self):
        """Generate comprehensive financial report for member"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Member Financial Report',
            'res_model': 'ams.member.financial.report.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_partner_id': self.id,
            }
        }
    
    def action_view_subscription_revenue_breakdown(self):
        """View revenue breakdown by subscription type"""
        return {
            'type': 'ir.actions.act_window',
            'name': f'Revenue Breakdown - {self.name}',
            'res_model': 'account.move.line',
            'view_mode': 'pivot,graph,tree',
            'domain': [
                ('partner_id', '=', self.id),
                ('move_id.subscription_id', '!=', False),
                ('account_id.account_type', '=', 'income'),
                ('move_id.state', '=', 'posted')
            ],
            'context': {
                'group_by': ['move_id.subscription_id.subscription_type_id'],
                'search_default_group_subscription_type': 1,
            }
        }
    
    def get_financial_summary_data(self):
        """Get financial summary data for member dashboard"""
        return {
            'basic_metrics': {
                'total_revenue': self.total_ams_revenue,
                'current_year_revenue': self.current_year_revenue,
                'last_year_revenue': self.last_year_revenue,
                'outstanding_balance': self.outstanding_ams_balance,
                'is_financial': self.is_financial_member,
            },
            'value_metrics': {
                'lifetime_value': self.customer_lifetime_value,
                'monthly_recurring_revenue': self.monthly_recurring_revenue,
                'annual_recurring_revenue': self.annual_recurring_revenue,
            },
            'payment_behavior': {
                'average_delay': self.average_payment_delay,
                'reliability_score': self.payment_reliability_score,
                'risk_level': self.payment_risk_level,
            },
            'membership_history': {
                'start_year': self.membership_start_year,
                'years_as_member': self.years_as_member,
                'gap_years': self.membership_gap_years,
            },
            'invoice_stats': {
                'total_invoices': self.total_ams_invoices,
                'paid_invoices': self.paid_invoices_count,
                'overdue_invoices': self.overdue_invoices_count,
            }
        }
    
    @api.model
    def get_member_financial_analytics(self, date_from=None, date_to=None):
        """Get aggregated member financial analytics"""
        if not date_from:
            date_from = fields.Date.today().replace(month=1, day=1)
        if not date_to:
            date_to = fields.Date.today()
        
        # Get all members with AMS activity
        members = self.search([('total_subscription_count', '>', 0)])
        
        analytics = {
            'total_members': len(members),
            'financial_members': len(members.filtered('is_financial_member')),
            'members_with_overdue': len(members.filtered(lambda m: m.overdue_invoices_count > 0)),
            'total_outstanding': sum(members.mapped('outstanding_ams_balance')),
            'total_revenue_period': sum(members.mapped('current_year_revenue')),
            'average_ltv': sum(members.mapped('customer_lifetime_value')) / len(members) if members else 0,
            'risk_distribution': {
                'low': len(members.filtered(lambda m: m.payment_risk_level == 'low')),
                'medium': len(members.filtered(lambda m: m.payment_risk_level == 'medium')),
                'high': len(members.filtered(lambda m: m.payment_risk_level == 'high')),
                'critical': len(members.filtered(lambda m: m.payment_risk_level == 'critical')),
            }
        }
        
        return analytics


class AMSPaymentPlan(models.Model):
    """
    Payment plan model for members with outstanding balances
    """
    _name = 'ams.payment.plan'
    _description = 'AMS Payment Plan'
    _order = 'create_date desc'
    
    partner_id = fields.Many2one('res.partner', 'Member', required=True)
    name = fields.Char('Plan Name', required=True)
    
    total_amount = fields.Float('Total Amount', required=True)
    down_payment = fields.Float('Down Payment', default=0.0)
    remaining_amount = fields.Float('Remaining Amount', compute='_compute_remaining_amount', store=True)
    
    number_of_payments = fields.Integer('Number of Payments', required=True, default=6)
    payment_frequency = fields.Selection([
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly')
    ], string='Payment Frequency', default='monthly', required=True)
    
    start_date = fields.Date('Start Date', required=True, default=fields.Date.today)
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled')
    ], string='Status', default='draft')
    
    payment_line_ids = fields.One2many('ams.payment.plan.line', 'payment_plan_id', 'Payment Schedule')
    
    notes = fields.Text('Notes')
    
    @api.depends('total_amount', 'down_payment')
    def _compute_remaining_amount(self):
        for plan in self:
            plan.remaining_amount = plan.total_amount - plan.down_payment
    
    @api.model
    def create(self, vals):
        if not vals.get('name'):
            vals['name'] = self.env['ir.sequence'].next_by_code('ams.payment.plan') or 'New Plan'
        return super().create(vals)
    
    def action_activate_plan(self):
        """Activate the payment plan and generate payment schedule"""
        self.state = 'active'
        self._generate_payment_schedule()
        
        # Update partner
        self.partner_id.has_payment_plan = True
        self.partner_id.payment_plan_id = self.id
    
    def action_cancel_plan(self):
        """Cancel the payment plan"""
        self.state = 'cancelled'
        self.partner_id.has_payment_plan = False
        self.partner_id.payment_plan_id = False
    
    def _generate_payment_schedule(self):
        """Generate payment schedule lines"""
        self.payment_line_ids.unlink()
        
        if self.remaining_amount <= 0:
            return
        
        payment_amount = self.remaining_amount / self.number_of_payments
        current_date = self.start_date
        
        for i in range(self.number_of_payments):
            line_vals = {
                'payment_plan_id': self.id,
                'sequence': i + 1,
                'due_date': current_date,
                'amount': payment_amount,
                'state': 'pending'
            }
            
            self.env['ams.payment.plan.line'].create(line_vals)
            
            # Calculate next payment date
            if self.payment_frequency == 'weekly':
                current_date += timedelta(weeks=1)
            elif self.payment_frequency == 'monthly':
                current_date += relativedelta(months=1)
            elif self.payment_frequency == 'quarterly':
                current_date += relativedelta(months=3)


class AMSPaymentPlanLine(models.Model):
    """
    Individual payment plan installments
    """
    _name = 'ams.payment.plan.line'
    _description = 'AMS Payment Plan Line'
    _order = 'due_date'
    
    payment_plan_id = fields.Many2one('ams.payment.plan', 'Payment Plan', required=True, ondelete='cascade')
    partner_id = fields.Many2one('res.partner', related='payment_plan_id.partner_id', store=True)
    
    sequence = fields.Integer('Sequence', required=True)
    due_date = fields.Date('Due Date', required=True)
    amount = fields.Float('Amount', required=True)
    
    state = fields.Selection([
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('overdue', 'Overdue'),
        ('cancelled', 'Cancelled')
    ], string='Status', default='pending')
    
    payment_id = fields.Many2one('account.payment', 'Payment')
    payment_date = fields.Date('Payment Date')
    
    def action_record_payment(self):
        """Record payment for this installment"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Record Payment',
            'res_model': 'account.payment.register',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_partner_id': self.partner_id.id,
                'default_amount': self.amount,
                'default_payment_plan_line_id': self.id,
            }
        }
