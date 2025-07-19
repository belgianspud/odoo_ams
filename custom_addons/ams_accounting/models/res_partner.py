from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import logging

_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    """
    Enhanced partner model with comprehensive AMS financial integration
    """
    _inherit = 'res.partner'
    
    # ========================
    # AMS MEMBER CLASSIFICATION
    # ========================
    
    is_ams_member = fields.Boolean('AMS Member', compute='_compute_ams_member_status', store=True)
    member_number = fields.Char('Member Number', index=True,
        help="Unique member identification number")
    member_type = fields.Selection([
        ('individual', 'Individual Member'),
        ('student', 'Student Member'),
        ('corporate', 'Corporate Member'),
        ('honorary', 'Honorary Member'),
        ('emeritus', 'Emeritus Member'),
        ('associate', 'Associate Member'),
        ('fellow', 'Fellow'),
        ('retired', 'Retired Member')
    ], string='Member Type', default='individual')
    
    member_status = fields.Selection([
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('suspended', 'Suspended'),
        ('pending', 'Pending Approval'),
        ('expired', 'Expired'),
        ('cancelled', 'Cancelled')
    ], string='Member Status', compute='_compute_ams_member_status', store=True)
    
    # ========================
    # MEMBERSHIP INFORMATION
    # ========================
    
    join_date = fields.Date('Join Date',
        help="Date when member first joined the organization")
    
    membership_start_date = fields.Date('Current Membership Start', compute='_compute_membership_dates', store=True)
    membership_end_date = fields.Date('Current Membership End', compute='_compute_membership_dates', store=True)
    membership_years = fields.Float('Years as Member', compute='_compute_membership_years', store=True)
    
    # Member Categories and Special Designations
    member_categories = fields.Many2many('ams.member.category', 'partner_member_category_rel',
                                        'partner_id', 'category_id', 'Member Categories')
    
    is_board_member = fields.Boolean('Board Member', default=False)
    is_committee_member = fields.Boolean('Committee Member', default=False)
    is_volunteer = fields.Boolean('Volunteer', default=False)
    
    # Professional Information
    professional_designation = fields.Char('Professional Designation')
    license_number = fields.Char('License Number')
    certification_ids = fields.One2many('ams.member.certification', 'partner_id', 'Certifications')
    
    # ========================
    # FINANCIAL INFORMATION
    # ========================
    
    # Enhanced Credit and Financial Status
    ams_credit_limit = fields.Float('AMS Credit Limit', default=0.0)
    ams_credit_used = fields.Float('AMS Credit Used', compute='_compute_ams_credit_usage', store=True)
    ams_credit_available = fields.Float('AMS Credit Available', compute='_compute_ams_credit_usage', store=True)
    
    # Payment Behavior and Risk
    payment_reliability_score = fields.Float('Payment Reliability Score', 
        compute='_compute_payment_metrics', store=True,
        help="Score from 0-100 based on payment history")
    
    average_payment_delay = fields.Float('Avg Payment Delay (Days)', 
        compute='_compute_payment_metrics', store=True)
    
    payment_risk_level = fields.Selection([
        ('low', 'Low Risk'),
        ('medium', 'Medium Risk'),
        ('high', 'High Risk'),
        ('critical', 'Critical Risk')
    ], string='Payment Risk Level', compute='_compute_payment_metrics', store=True)
    
    # Financial Status Flags
    is_financial_member = fields.Boolean('Financial Member', 
        compute='_compute_financial_status', store=True,
        help="Member has paid all outstanding balances")
    
    has_overdue_balance = fields.Boolean('Has Overdue Balance', 
        compute='_compute_financial_status', store=True)
    
    financial_hold = fields.Boolean('Financial Hold', default=False,
        help="Member account is on financial hold")
    
    # ========================
    # SUBSCRIPTION TRACKING
    # ========================
    
    # Current Subscriptions
    active_subscription_count = fields.Integer('Active Subscriptions', 
        compute='_compute_subscription_counts', store=True)
    total_subscription_count = fields.Integer('Total Subscriptions', 
        compute='_compute_subscription_counts', store=True)
    expired_subscription_count = fields.Integer('Expired Subscriptions', 
        compute='_compute_subscription_counts', store=True)
    pending_renewal_count = fields.Integer('Pending Renewals', 
        compute='_compute_subscription_counts', store=True)
    
    # Primary Membership Tracking
    current_membership_id = fields.Many2one('ams.subscription', 'Current Membership',
        compute='_compute_current_membership', store=True)
    next_renewal_date = fields.Date('Next Renewal Date', 
        compute='_compute_current_membership', store=True)
    auto_renewal_enabled = fields.Boolean('Auto Renewal Enabled', 
        compute='_compute_current_membership', store=True)
    
    # Subscription Financial Metrics
    total_subscription_value = fields.Float('Total Subscription Value', 
        compute='_compute_subscription_financials', store=True)
    monthly_recurring_revenue = fields.Float('Member MRR', 
        compute='_compute_subscription_financials', store=True)
    annual_recurring_revenue = fields.Float('Member ARR', 
        compute='_compute_subscription_financials', store=True)
    customer_lifetime_value = fields.Float('Customer Lifetime Value', 
        compute='_compute_subscription_financials', store=True)
    
    # ========================
    # COMMUNICATION PREFERENCES
    # ========================
    
    # Financial Communication
    financial_communication_method = fields.Selection([
        ('email', 'Email'),
        ('mail', 'Postal Mail'),
        ('phone', 'Phone'),
        ('portal', 'Member Portal'),
        ('sms', 'SMS')
    ], string='Financial Communication Method', default='email')
    
    suppress_financial_emails = fields.Boolean('Suppress Financial Emails', default=False)
    suppress_marketing_emails = fields.Boolean('Suppress Marketing Emails', default=False)
    
    # Portal and Digital Access
    portal_access_enabled = fields.Boolean('Portal Access Enabled', default=True)
    digital_statements = fields.Boolean('Digital Statements Only', default=True)
    
    # ========================
    # CHAPTER RELATIONSHIPS
    # ========================
    
    primary_chapter_id = fields.Many2one('ams.chapter', 'Primary Chapter')
    chapter_ids = fields.Many2many('ams.chapter', 'partner_chapter_rel',
                                  'partner_id', 'chapter_id', 'Member Chapters',
                                  compute='_compute_member_chapters', store=True)
    
    # ========================
    # COMPUTED FIELDS
    # ========================
    
    @api.depends('subscription_ids', 'subscription_ids.state', 'subscription_ids.subscription_code')
    def _compute_ams_member_status(self):
        for partner in self:
            # Check if partner has any subscriptions
            subscriptions = partner.subscription_ids
            partner.is_ams_member = bool(subscriptions)
            
            if not subscriptions:
                partner.member_status = 'inactive'
                continue
            
            # Determine status based on active membership subscriptions
            membership_subs = subscriptions.filtered(lambda s: s.subscription_code == 'membership')
            
            if not membership_subs:
                partner.member_status = 'inactive'
            elif any(sub.state == 'active' for sub in membership_subs):
                partner.member_status = 'active'
            elif any(sub.state == 'pending_renewal' for sub in membership_subs):
                partner.member_status = 'pending'
            elif any(sub.state == 'expired' for sub in membership_subs):
                partner.member_status = 'expired'
            else:
                partner.member_status = 'inactive'
    
    @api.depends('subscription_ids', 'subscription_ids.start_date', 'subscription_ids.end_date', 'subscription_ids.state')
    def _compute_membership_dates(self):
        for partner in self:
            active_memberships = partner.subscription_ids.filtered(
                lambda s: s.subscription_code == 'membership' and s.state == 'active'
            ).sorted('start_date')
            
            if active_memberships:
                partner.membership_start_date = active_memberships[0].start_date
                partner.membership_end_date = max(active_memberships.mapped('end_date')) if any(active_memberships.mapped('end_date')) else False
            else:
                partner.membership_start_date = False
                partner.membership_end_date = False
    
    @api.depends('join_date', 'membership_start_date')
    def _compute_membership_years(self):
        for partner in self:
            if partner.join_date:
                today = fields.Date.today()
                years = (today - partner.join_date).days / 365.25
                partner.membership_years = round(years, 1)
            else:
                partner.membership_years = 0.0
    
    @api.depends('ams_credit_limit', 'invoice_ids', 'invoice_ids.amount_residual')
    def _compute_ams_credit_usage(self):
        for partner in self:
            # Calculate outstanding invoices for AMS subscriptions
            outstanding_invoices = partner.invoice_ids.filtered(
                lambda inv: inv.move_type == 'out_invoice' and 
                           inv.state == 'posted' and 
                           inv.amount_residual > 0 and
                           (inv.is_ams_subscription_invoice or inv.ams_subscription_id)
            )
            
            partner.ams_credit_used = sum(outstanding_invoices.mapped('amount_residual'))
            partner.ams_credit_available = max(0, partner.ams_credit_limit - partner.ams_credit_used)
    
    @api.depends('invoice_ids', 'invoice_ids.payment_state', 'invoice_ids.invoice_date_due', 'invoice_ids.payment_date')
    def _compute_payment_metrics(self):
        for partner in self:
            ams_invoices = partner.invoice_ids.filtered(
                lambda inv: inv.move_type == 'out_invoice' and 
                           inv.state == 'posted' and
                           (inv.is_ams_subscription_invoice or inv.ams_subscription_id)
            )
            
            if not ams_invoices:
                partner.payment_reliability_score = 100.0
                partner.average_payment_delay = 0.0
                partner.payment_risk_level = 'low'
                continue
            
            # Calculate payment delays for paid invoices
            paid_invoices = ams_invoices.filtered(
                lambda inv: inv.payment_state == 'paid' and inv.payment_date and inv.invoice_date_due
            )
            
            if paid_invoices:
                delays = []
                for invoice in paid_invoices:
                    delay = (invoice.payment_date - invoice.invoice_date_due).days
                    delays.append(max(0, delay))  # Only positive delays
                
                partner.average_payment_delay = sum(delays) / len(delays) if delays else 0.0
            else:
                partner.average_payment_delay = 0.0
            
            # Calculate reliability score
            total_invoices = len(ams_invoices)
            paid_on_time = len([inv for inv in paid_invoices 
                               if not inv.invoice_date_due or inv.payment_date <= inv.invoice_date_due])
            
            overdue_count = len(ams_invoices.filtered(
                lambda inv: inv.invoice_date_due and 
                           inv.invoice_date_due < fields.Date.today() and
                           inv.payment_state in ['not_paid', 'partial']
            ))
            
            if total_invoices > 0:
                on_time_ratio = paid_on_time / total_invoices
                base_score = on_time_ratio * 100
                
                # Penalties
                overdue_penalty = min(50, overdue_count * 10)
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
    
    @api.depends('ams_credit_used', 'invoice_ids', 'invoice_ids.amount_residual', 'invoice_ids.invoice_date_due')
    def _compute_financial_status(self):
        for partner in self:
            partner.is_financial_member = (partner.ams_credit_used <= 0.01)  # Allow for rounding
            
            # Check for overdue balances
            today = fields.Date.today()
            overdue_invoices = partner.invoice_ids.filtered(
                lambda inv: inv.move_type == 'out_invoice' and
                           inv.state == 'posted' and
                           inv.amount_residual > 0 and
                           inv.invoice_date_due and
                           inv.invoice_date_due < today and
                           (inv.is_ams_subscription_invoice or inv.ams_subscription_id)
            )
            
            partner.has_overdue_balance = bool(overdue_invoices)
    
    @api.depends('subscription_ids', 'subscription_ids.state')
    def _compute_subscription_counts(self):
        for partner in self:
            subscriptions = partner.subscription_ids
            
            partner.total_subscription_count = len(subscriptions)
            partner.active_subscription_count = len(subscriptions.filtered(lambda s: s.state == 'active'))
            partner.expired_subscription_count = len(subscriptions.filtered(lambda s: s.state == 'expired'))
            partner.pending_renewal_count = len(subscriptions.filtered(lambda s: s.state == 'pending_renewal'))
    
    @api.depends('subscription_ids', 'subscription_ids.state', 'subscription_ids.subscription_code')
    def _compute_current_membership(self):
        for partner in self:
            # Find most recent active membership
            active_memberships = partner.subscription_ids.filtered(
                lambda s: s.subscription_code == 'membership' and s.state == 'active'
            ).sorted('start_date', reverse=True)
            
            if active_memberships:
                membership = active_memberships[0]
                partner.current_membership_id = membership.id
                partner.next_renewal_date = membership.next_renewal_date
                partner.auto_renewal_enabled = membership.auto_renewal
            else:
                partner.current_membership_id = False
                partner.next_renewal_date = False
                partner.auto_renewal_enabled = False
    
    @api.depends('subscription_ids', 'subscription_ids.amount', 'subscription_ids.state')
    def _compute_subscription_financials(self):
        for partner in self:
            subscriptions = partner.subscription_ids
            active_subs = subscriptions.filtered(lambda s: s.state == 'active')
            
            partner.total_subscription_value = sum(subscriptions.mapped('amount'))
            partner.monthly_recurring_revenue = sum(active_subs.mapped('monthly_recurring_revenue'))
            partner.annual_recurring_revenue = sum(active_subs.mapped('annual_recurring_revenue'))
            partner.customer_lifetime_value = sum(subscriptions.mapped('lifetime_value'))
    
    @api.depends('subscription_ids', 'subscription_ids.chapter_id', 'subscription_ids.state')
    def _compute_member_chapters(self):
        for partner in self:
            active_chapter_subs = partner.subscription_ids.filtered(
                lambda s: s.subscription_code == 'chapter' and s.state == 'active' and s.chapter_id
            )
            partner.chapter_ids = [(6, 0, active_chapter_subs.mapped('chapter_id').ids)]
    
    # ========================
    # BUSINESS METHODS
    # ========================
    
    @api.model_create_multi
    def create(self, vals_list):
        partners = super().create(vals_list)
        
        for partner in partners:
            # Auto-generate member number if not provided
            if not partner.member_number and partner.is_ams_member:
                partner.member_number = self._generate_member_number()
        
        return partners
    
    def _generate_member_number(self):
        """Generate unique member number"""
        sequence = self.env['ir.sequence'].search([('code', '=', 'ams.member.number')], limit=1)
        if not sequence:
            sequence = self.env['ir.sequence'].create({
                'name': 'AMS Member Number',
                'code': 'ams.member.number',
                'prefix': 'AMS-',
                'padding': 6,
                'number_increment': 1,
            })
        
        return sequence.next_by_id()
    
    def action_view_active_subscriptions(self):
        """View active subscriptions for this member"""
        return {
            'type': 'ir.actions.act_window',
            'name': f'{self.name} - Active Subscriptions',
            'res_model': 'ams.subscription',
            'view_mode': 'tree,form',
            'domain': [('partner_id', '=', self.id), ('state', '=', 'active')],
            'context': {'default_partner_id': self.id}
        }
    
    def action_view_all_subscriptions(self):
        """View all subscriptions for this member"""
        return {
            'type': 'ir.actions.act_window',
            'name': f'{self.name} - All Subscriptions',
            'res_model': 'ams.subscription',
            'view_mode': 'tree,form',
            'domain': [('partner_id', '=', self.id)],
            'context': {'default_partner_id': self.id}
        }
    
    def action_create_membership(self):
        """Create new membership subscription"""
        membership_type = self.env['ams.subscription.type'].search([('code', '=', 'membership')], limit=1)
        
        return {
            'type': 'ir.actions.act_window',
            'name': 'Create Membership',
            'res_model': 'ams.subscription',
            'view_mode': 'form',
            'context': {
                'default_partner_id': self.id,
                'default_subscription_type_id': membership_type.id if membership_type else False,
            }
        }
    
    def action_financial_summary(self):
        """View financial summary for this member"""
        return {
            'type': 'ir.actions.act_window',
            'name': f'Financial Summary - {self.name}',
            'res_model': 'ams.member.financial.summary.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_partner_id': self.id}
        }
    
    def action_enable_auto_renewal(self):
        """Enable auto renewal for active subscriptions"""
        active_subs = self.subscription_ids.filtered(lambda s: s.state == 'active' and s.is_recurring)
        active_subs.write({'auto_renewal': True})
        
        self.message_post(body=_('Auto-renewal enabled for all active subscriptions.'))
    
    def action_disable_auto_renewal(self):
        """Disable auto renewal for active subscriptions"""
        active_subs = self.subscription_ids.filtered(lambda s: s.state == 'active' and s.is_recurring)
        active_subs.write({'auto_renewal': False})
        
        self.message_post(body=_('Auto-renewal disabled for all active subscriptions.'))
    
    def action_place_financial_hold(self):
        """Place member on financial hold"""
        self.financial_hold = True
        self.message_post(
            body=_('Member placed on financial hold.'),
            subject=_('Financial Hold Applied')
        )
    
    def action_remove_financial_hold(self):
        """Remove member from financial hold"""
        self.financial_hold = False
        self.message_post(
            body=_('Member removed from financial hold.'),
            subject=_('Financial Hold Removed')
        )
    
    def action_send_financial_statement(self):
        """Send financial statement to member"""
        if self.suppress_financial_emails:
            raise UserError(_('Financial emails are suppressed for this member.'))
        
        template = self.env.ref('ams_accounting.email_template_financial_statement', False)
        if template:
            template.send_mail(self.id, force_send=True)
            self.message_post(body=_('Financial statement sent via email.'))
        else:
            raise UserError(_('Financial statement email template not found.'))
    
    def check_credit_limit(self, amount):
        """Check if member can make a purchase of given amount"""
        if self.financial_hold:
            return False, _('Member account is on financial hold.')
        
        if self.ams_credit_limit <= 0:
            return True, ''  # No credit limit set
        
        if amount > self.ams_credit_available:
            return False, _('Insufficient credit available. Required: %s, Available: %s') % (amount, self.ams_credit_available)
        
        return True, ''
    
    def get_member_dashboard_data(self):
        """Get dashboard data for member portal"""
        return {
            'member_info': {
                'member_number': self.member_number,
                'member_type': self.member_type,
                'member_status': self.member_status,
                'join_date': self.join_date,
                'membership_years': self.membership_years,
            },
            'financial_status': {
                'is_financial': self.is_financial_member,
                'credit_used': self.ams_credit_used,
                'credit_available': self.ams_credit_available,
                'payment_score': self.payment_reliability_score,
                'has_overdue': self.has_overdue_balance,
            },
            'subscriptions': {
                'active_count': self.active_subscription_count,
                'total_count': self.total_subscription_count,
                'next_renewal': self.next_renewal_date,
                'auto_renewal': self.auto_renewal_enabled,
                'pending_renewals': self.pending_renewal_count,
            },
            'financial_metrics': {
                'total_value': self.total_subscription_value,
                'monthly_revenue': self.monthly_recurring_revenue,
                'annual_revenue': self.annual_recurring_revenue,
                'lifetime_value': self.customer_lifetime_value,
            }
        }
    
    @api.model
    def get_member_analytics(self):
        """Get aggregated member analytics for dashboard"""
        members = self.search([('is_ams_member', '=', True)])
        
        return {
            'total_members': len(members),
            'active_members': len(members.filtered(lambda m: m.member_status == 'active')),
            'financial_members': len(members.filtered('is_financial_member')),
            'members_with_overdue': len(members.filtered('has_overdue_balance')),
            'members_on_hold': len(members.filtered('financial_hold')),
            'average_membership_years': sum(members.mapped('membership_years')) / len(members) if members else 0,
            'total_mrr': sum(members.mapped('monthly_recurring_revenue')),
            'total_arr': sum(members.mapped('annual_recurring_revenue')),
            'average_ltv': sum(members.mapped('customer_lifetime_value')) / len(members) if members else 0,
            'risk_distribution': {
                'low': len(members.filtered(lambda m: m.payment_risk_level == 'low')),
                'medium': len(members.filtered(lambda m: m.payment_risk_level == 'medium')),
                'high': len(members.filtered(lambda m: m.payment_risk_level == 'high')),
                'critical': len(members.filtered(lambda m: m.payment_risk_level == 'critical')),
            }
        }


class AMSMemberCategory(models.Model):
    """
    Categories for member classification
    """
    _name = 'ams.member.category'
    _description = 'AMS Member Category'
    _order = 'name'
    
    name = fields.Char('Category Name', required=True, translate=True)
    description = fields.Text('Description')
    color = fields.Integer('Color Index', default=0)
    
    member_count = fields.Integer('Member Count', compute='_compute_member_count')
    
    @api.depends('partner_ids')
    def _compute_member_count(self):
        for category in self:
            category.member_count = len(category.partner_ids)
    
    partner_ids = fields.Many2many('res.partner', 'partner_member_category_rel',
                                  'category_id', 'partner_id', 'Members')


class AMSMemberCertification(models.Model):
    """
    Member certifications and credentials
    """
    _name = 'ams.member.certification'
    _description = 'AMS Member Certification'
    _order = 'issue_date desc'
    
    partner_id = fields.Many2one('res.partner', 'Member', required=True, ondelete='cascade')
    
    name = fields.Char('Certification Name', required=True)
    issuing_organization = fields.Char('Issuing Organization')
    certification_number = fields.Char('Certification Number')
    
    issue_date = fields.Date('Issue Date')
    expiry_date = fields.Date('Expiry Date')
    
    status = fields.Selection([
        ('active', 'Active'),
        ('expired', 'Expired'),
        ('suspended', 'Suspended'),
        ('revoked', 'Revoked')
    ], string='Status', default='active')
    
    notes = fields.Text('Notes')
    
    def name_get(self):
        result = []
        for cert in self:
            name = f"{cert.name}"
            if cert.certification_number:
                name += f" ({cert.certification_number})"
            result.append((cert.id, name))
        return result