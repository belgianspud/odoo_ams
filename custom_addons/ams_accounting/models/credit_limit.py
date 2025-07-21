from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import logging

_logger = logging.getLogger(__name__)


class AMSCreditLimit(models.Model):
    """
    Model for managing member credit limits with AMS-specific features
    """
    _name = 'ams.credit.limit'
    _description = 'AMS Credit Limit'
    _order = 'partner_id, create_date desc'
    
    partner_id = fields.Many2one('res.partner', 'Member', required=True)
    credit_limit = fields.Float('Credit Limit', required=True, default=0.0)
    
    # Limit Types
    limit_type = fields.Selection([
        ('membership', 'Membership Credit'),
        ('chapter', 'Chapter Fees Credit'),
        ('general', 'General Credit'),
        ('temporary', 'Temporary Increase'),
        ('emergency', 'Emergency Credit')
    ], string='Credit Type', default='general', required=True)
    
    # Date Management
    effective_date = fields.Date('Effective Date', required=True, default=fields.Date.today)
    expiry_date = fields.Date('Expiry Date',
        help="Leave blank for permanent credit limit")
    
    # Approval and Authorization
    approved_by = fields.Many2one('res.users', 'Approved By', required=True, default=lambda self: self.env.user)
    approval_date = fields.Date('Approval Date', required=True, default=fields.Date.today)
    approval_notes = fields.Text('Approval Notes')
    
    # Status and Tracking
    state = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('expired', 'Expired'),
        ('suspended', 'Suspended'),
        ('cancelled', 'Cancelled')
    ], string='Status', default='draft', tracking=True)
    
    # Usage Tracking
    credit_used = fields.Float('Credit Used', compute='_compute_credit_usage', store=True)
    credit_available = fields.Float('Credit Available', compute='_compute_credit_usage', store=True)
    utilization_percentage = fields.Float('Utilization %', compute='_compute_credit_usage', store=True)
    
    # Risk Management
    risk_assessment = fields.Selection([
        ('low', 'Low Risk'),
        ('medium', 'Medium Risk'),
        ('high', 'High Risk'),
        ('critical', 'Critical Risk')
    ], string='Risk Assessment', compute='_compute_risk_assessment', store=True)
    
    # Notifications
    notify_at_percentage = fields.Float('Notify at %', default=80.0,
        help="Send notification when credit utilization reaches this percentage")
    last_notification_date = fields.Date('Last Notification Date')
    
    # Related Models
    credit_hold_ids = fields.One2many('ams.credit.hold', 'credit_limit_id', 'Credit Holds')
    credit_usage_ids = fields.One2many('ams.credit.usage', 'credit_limit_id', 'Credit Usage History')
    
    @api.depends('partner_id')
    def _compute_credit_usage(self):
        for limit in self:
            if limit.state != 'active':
                limit.credit_used = 0.0
                limit.credit_available = 0.0
                limit.utilization_percentage = 0.0
                continue
            
            # Calculate current credit usage from outstanding invoices
            outstanding_invoices = self.env['account.move'].search([
                ('partner_id', '=', limit.partner_id.id),
                ('move_type', '=', 'out_invoice'),
                ('state', '=', 'posted'),
                ('payment_state', 'in', ['not_paid', 'partial']),
                ('is_ams_subscription_invoice', '=', True)
            ])
            
            total_outstanding = sum(outstanding_invoices.mapped('amount_residual'))
            
            # Add any credit holds
            active_holds = limit.credit_hold_ids.filtered(lambda h: h.state == 'active')
            hold_amount = sum(active_holds.mapped('hold_amount'))
            
            limit.credit_used = total_outstanding + hold_amount
            limit.credit_available = max(0, limit.credit_limit - limit.credit_used)
            
            if limit.credit_limit > 0:
                limit.utilization_percentage = (limit.credit_used / limit.credit_limit) * 100
            else:
                limit.utilization_percentage = 0.0
    
    @api.depends('utilization_percentage', 'partner_id')
    def _compute_risk_assessment(self):
        for limit in self:
            if not limit.partner_id:
                limit.risk_assessment = 'medium'
                continue
            
            # Base risk on utilization
            utilization = limit.utilization_percentage
            
            # Get member's payment history
            payment_score = limit.partner_id.payment_reliability_score if hasattr(limit.partner_id, 'payment_reliability_score') else 75
            
            # Calculate risk score
            risk_score = 0
            
            # Utilization risk
            if utilization > 90:
                risk_score += 40
            elif utilization > 80:
                risk_score += 30
            elif utilization > 60:
                risk_score += 20
            elif utilization > 40:
                risk_score += 10
            
            # Payment history risk
            if payment_score < 40:
                risk_score += 40
            elif payment_score < 60:
                risk_score += 30
            elif payment_score < 80:
                risk_score += 20
            else:
                risk_score += 0
            
            # Overdue invoices risk
            overdue_count = getattr(limit.partner_id, 'overdue_invoices_count', 0)
            risk_score += min(20, overdue_count * 5)
            
            # Determine risk level
            if risk_score < 20:
                limit.risk_assessment = 'low'
            elif risk_score < 40:
                limit.risk_assessment = 'medium'
            elif risk_score < 60:
                limit.risk_assessment = 'high'
            else:
                limit.risk_assessment = 'critical'
    
    @api.model
    def create(self, vals):
        credit_limit = super().create(vals)
        
        # Auto-activate if conditions are met
        if credit_limit.state == 'draft' and credit_limit.effective_date <= fields.Date.today():
            credit_limit.action_activate()
        
        return credit_limit
    
    def action_activate(self):
        """Activate the credit limit"""
        for limit in self:
            if limit.effective_date > fields.Date.today():
                raise UserError(_('Cannot activate credit limit before effective date.'))
            
            # Deactivate other active limits of the same type
            other_limits = self.search([
                ('partner_id', '=', limit.partner_id.id),
                ('limit_type', '=', limit.limit_type),
                ('state', '=', 'active'),
                ('id', '!=', limit.id)
            ])
            other_limits.write({'state': 'suspended'})
            
            limit.state = 'active'
            
            # Update partner's credit limit
            if limit.limit_type == 'general':
                limit.partner_id.credit_limit = limit.credit_limit
            elif limit.limit_type == 'membership':
                limit.partner_id.ams_credit_limit = limit.credit_limit
            
            # Log the activation
            limit.message_post(
                body=_('Credit limit activated: %s') % limit.credit_limit,
                subject=_('Credit Limit Activated')
            )
    
    def action_suspend(self):
        """Suspend the credit limit"""
        for limit in self:
            limit.state = 'suspended'
            limit.message_post(
                body=_('Credit limit suspended'),
                subject=_('Credit Limit Suspended')
            )
    
    def action_cancel(self):
        """Cancel the credit limit"""
        for limit in self:
            if limit.credit_used > 0:
                raise UserError(_('Cannot cancel credit limit with outstanding usage.'))
            
            limit.state = 'cancelled'
            limit.message_post(
                body=_('Credit limit cancelled'),
                subject=_('Credit Limit Cancelled')
            )
    
    def action_extend_expiry(self):
        """Extend credit limit expiry date"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Extend Credit Limit',
            'res_model': 'ams.credit.limit.extend.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_credit_limit_id': self.id,
                'default_current_expiry': self.expiry_date,
            }
        }
    
    def action_create_hold(self):
        """Create a credit hold"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Create Credit Hold',
            'res_model': 'ams.credit.hold',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_credit_limit_id': self.id,
                'default_partner_id': self.partner_id.id,
            }
        }
    
    def check_credit_availability(self, amount):
        """Check if credit is available for a given amount"""
        if self.state != 'active':
            return False, _('Credit limit is not active')
        
        if self.expiry_date and self.expiry_date < fields.Date.today():
            return False, _('Credit limit has expired')
        
        if amount > self.credit_available:
            return False, _('Insufficient credit available. Required: %s, Available: %s') % (amount, self.credit_available)
        
        return True, _('Credit available')
    
    def reserve_credit(self, amount, description=''):
        """Reserve credit for a transaction"""
        available, message = self.check_credit_availability(amount)
        
        if not available:
            raise UserError(message)
        
        # Create credit hold
        hold_vals = {
            'credit_limit_id': self.id,
            'partner_id': self.partner_id.id,
            'hold_amount': amount,
            'description': description or 'Credit reservation',
            'hold_type': 'reservation',
            'state': 'active'
        }
        
        hold = self.env['ams.credit.hold'].create(hold_vals)
        return hold
    
    def send_utilization_notification(self):
        """Send notification about credit utilization"""
        if self.utilization_percentage >= self.notify_at_percentage:
            template = self.env.ref('ams_accounting.email_template_credit_utilization', False)
            if template:
                template.send_mail(self.id, force_send=True)
                self.last_notification_date = fields.Date.today()
    
    @api.model
    def _cron_check_credit_limits(self):
        """Cron job to check and update credit limits"""
        today = fields.Date.today()
        
        # Expire expired limits
        expired_limits = self.search([
            ('state', '=', 'active'),
            ('expiry_date', '<', today),
            ('expiry_date', '!=', False)
        ])
        
        for limit in expired_limits:
            limit.state = 'expired'
            limit.message_post(body=_('Credit limit expired'))
        
        # Send utilization notifications
        high_utilization_limits = self.search([
            ('state', '=', 'active'),
            ('utilization_percentage', '>=', 80),
            '|', ('last_notification_date', '<', today - timedelta(days=7)),
            ('last_notification_date', '=', False)
        ])
        
        for limit in high_utilization_limits:
            limit.send_utilization_notification()
        
        _logger.info(f"Expired {len(expired_limits)} credit limits, sent {len(high_utilization_limits)} notifications")
    
    @api.model
    def get_member_credit_summary(self, partner_id):
        """Get comprehensive credit summary for a member"""
        partner = self.env['res.partner'].browse(partner_id)
        
        active_limits = self.search([
            ('partner_id', '=', partner_id),
            ('state', '=', 'active')
        ])
        
        summary = {
            'total_credit_limit': sum(active_limits.mapped('credit_limit')),
            'total_credit_used': sum(active_limits.mapped('credit_used')),
            'total_credit_available': sum(active_limits.mapped('credit_available')),
            'overall_utilization': 0.0,
            'highest_risk_level': 'low',
            'limits_by_type': {},
            'active_holds': [],
            'credit_history': []
        }
        
        if summary['total_credit_limit'] > 0:
            summary['overall_utilization'] = (summary['total_credit_used'] / summary['total_credit_limit']) * 100
        
        # Risk assessment
        risk_levels = ['low', 'medium', 'high', 'critical']
        highest_risk_index = 0
        
        for limit in active_limits:
            # Limits by type
            summary['limits_by_type'][limit.limit_type] = {
                'limit': limit.credit_limit,
                'used': limit.credit_used,
                'available': limit.credit_available,
                'utilization': limit.utilization_percentage,
                'risk': limit.risk_assessment
            }
            
            # Track highest risk
            if limit.risk_assessment in risk_levels:
                risk_index = risk_levels.index(limit.risk_assessment)
                if risk_index > highest_risk_index:
                    highest_risk_index = risk_index
        
        summary['highest_risk_level'] = risk_levels[highest_risk_index]
        
        # Active holds
        active_holds = self.env['ams.credit.hold'].search([
            ('partner_id', '=', partner_id),
            ('state', '=', 'active')
        ])
        
        summary['active_holds'] = [{
            'amount': hold.hold_amount,
            'description': hold.description,
            'date': hold.create_date,
            'type': hold.hold_type
        } for hold in active_holds]
        
        return summary


class AMSCreditHold(models.Model):
    """
    Model for managing credit holds and reservations
    """
    _name = 'ams.credit.hold'
    _description = 'AMS Credit Hold'
    _order = 'create_date desc'
    
    credit_limit_id = fields.Many2one('ams.credit.limit', 'Credit Limit', required=True)
    partner_id = fields.Many2one('res.partner', 'Member', required=True)
    
    hold_amount = fields.Float('Hold Amount', required=True)
    description = fields.Char('Description', required=True)
    
    hold_type = fields.Selection([
        ('reservation', 'Credit Reservation'),
        ('security', 'Security Hold'),
        ('dispute', 'Dispute Hold'),
        ('collection', 'Collection Hold'),
        ('other', 'Other')
    ], string='Hold Type', default='reservation', required=True)
    
    # Date Management
    hold_date = fields.Date('Hold Date', required=True, default=fields.Date.today)
    release_date = fields.Date('Release Date')
    expiry_date = fields.Date('Auto-Release Date',
        help="Date when hold will be automatically released")
    
    # Status
    state = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('released', 'Released'),
        ('expired', 'Expired')
    ], string='Status', default='draft', tracking=True)
    
    # Authorization
    authorized_by = fields.Many2one('res.users', 'Authorized By', required=True, default=lambda self: self.env.user)
    release_authorized_by = fields.Many2one('res.users', 'Release Authorized By')
    
    # Related Transaction
    invoice_id = fields.Many2one('account.move', 'Related Invoice')
    payment_id = fields.Many2one('account.payment', 'Related Payment')
    
    def action_activate(self):
        """Activate the credit hold"""
        for hold in self:
            # Check if enough credit is available
            available, message = hold.credit_limit_id.check_credit_availability(hold.hold_amount)
            
            if not available and hold.hold_type not in ['security', 'dispute', 'collection']:
                raise UserError(message)
            
            hold.state = 'active'
            hold.message_post(body=_('Credit hold activated'))
    
    def action_release(self):
        """Release the credit hold"""
        for hold in self:
            hold.state = 'released'
            hold.release_date = fields.Date.today()
            hold.release_authorized_by = self.env.user.id
            hold.message_post(body=_('Credit hold released'))
    
    @api.model
    def _cron_auto_release_holds(self):
        """Automatically release expired holds"""
        today = fields.Date.today()
        
        expired_holds = self.search([
            ('state', '=', 'active'),
            ('expiry_date', '<', today),
            ('expiry_date', '!=', False)
        ])
        
        for hold in expired_holds:
            hold.state = 'expired'
            hold.release_date = today
            hold.message_post(body=_('Credit hold auto-released due to expiry'))
        
        return len(expired_holds)


class AMSCreditUsage(models.Model):
    """
    Model for tracking credit usage history
    """
    _name = 'ams.credit.usage'
    _description = 'AMS Credit Usage History'
    _order = 'create_date desc'
    
    credit_limit_id = fields.Many2one('ams.credit.limit', 'Credit Limit', required=True)
    partner_id = fields.Many2one('res.partner', 'Member', required=True)
    
    usage_amount = fields.Float('Usage Amount', required=True)
    usage_type = fields.Selection([
        ('increase', 'Credit Increase'),
        ('decrease', 'Credit Decrease'),
        ('payment', 'Payment Applied'),
        ('invoice', 'Invoice Created'),
        ('adjustment', 'Manual Adjustment')
    ], string='Usage Type', required=True)
    
    description = fields.Char('Description', required=True)
    reference = fields.Char('Reference')
    
    # Related Documents
    invoice_id = fields.Many2one('account.move', 'Related Invoice')
    payment_id = fields.Many2one('account.payment', 'Related Payment')
    
    # Balances
    previous_balance = fields.Float('Previous Balance')
    new_balance = fields.Float('New Balance')
    
    def name_get(self):
        result = []
        for usage in self:
            name = f"{usage.usage_type.title()}: {usage.usage_amount} - {usage.description}"
            result.append((usage.id, name))
        return result


class ResPartnerCreditLimit(models.Model):
    """
    Enhanced partner model with AMS credit limit integration
    """
    _inherit = 'res.partner'
    
    # Credit Limit Management
    ams_credit_limit_ids = fields.One2many('ams.credit.limit', 'partner_id', 'AMS Credit Limits')
    current_credit_limit = fields.Float('Current Credit Limit', compute='_compute_current_credit_info')
    credit_used = fields.Float('Credit Used', compute='_compute_current_credit_info')
    credit_available = fields.Float('Credit Available', compute='_compute_current_credit_info')
    credit_utilization = fields.Float('Credit Utilization %', compute='_compute_current_credit_info')
    
    # Credit Status
    credit_status = fields.Selection([
        ('good', 'Good Standing'),
        ('watch', 'Watch List'),
        ('hold', 'Credit Hold'),
        ('suspended', 'Suspended'),
        ('blocked', 'Blocked')
    ], string='Credit Status', default='good', compute='_compute_credit_status')
    
    # Alerts
    credit_alert = fields.Boolean('Credit Alert', compute='_compute_credit_alerts')
    credit_alert_message = fields.Text('Credit Alert Message', compute='_compute_credit_alerts')
    
    @api.depends('ams_credit_limit_ids', 'ams_credit_limit_ids.state')
    def _compute_current_credit_info(self):
        for partner in self:
            active_limits = partner.ams_credit_limit_ids.filtered(lambda l: l.state == 'active')
            
            partner.current_credit_limit = sum(active_limits.mapped('credit_limit'))
            partner.credit_used = sum(active_limits.mapped('credit_used'))
            partner.credit_available = sum(active_limits.mapped('credit_available'))
            
            if partner.current_credit_limit > 0:
                partner.credit_utilization = (partner.credit_used / partner.current_credit_limit) * 100
            else:
                partner.credit_utilization = 0.0
    
    @api.depends('credit_utilization', 'ams_credit_limit_ids')
    def _compute_credit_status(self):
        for partner in self:
            if partner.credit_utilization >= 100:
                partner.credit_status = 'blocked'
            elif partner.credit_utilization >= 90:
                partner.credit_status = 'hold'
            elif partner.credit_utilization >= 80:
                partner.credit_status = 'watch'
            else:
                partner.credit_status = 'good'
    
    @api.depends('credit_utilization', 'credit_status')
    def _compute_credit_alerts(self):
        for partner in self:
            partner.credit_alert = False
            partner.credit_alert_message = ''
            
            if partner.credit_status == 'blocked':
                partner.credit_alert = True
                partner.credit_alert_message = 'Credit limit exceeded. No new charges allowed.'
            elif partner.credit_status == 'hold':
                partner.credit_alert = True
                partner.credit_alert_message = 'Credit utilization critical. Requires approval for new charges.'
            elif partner.credit_status == 'watch':
                partner.credit_alert = True
                partner.credit_alert_message = 'High credit utilization. Monitor closely.'
    
    def action_view_credit_limits(self):
        """View credit limits for this partner"""
        return {
            'type': 'ir.actions.act_window',
            'name': f'Credit Limits - {self.name}',
            'res_model': 'ams.credit.limit',
            'view_mode': 'tree,form',
            'domain': [('partner_id', '=', self.id)],
            'context': {'default_partner_id': self.id}
        }
    
    def action_create_credit_limit(self):
        """Create new credit limit"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Create Credit Limit',
            'res_model': 'ams.credit.limit',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_partner_id': self.id}
        }
    
    def check_credit_limit(self, amount):
        """Check if member can make a purchase of given amount"""
        if not self.ams_credit_limit_ids:
            return True, ''
        
        active_limits = self.ams_credit_limit_ids.filtered(lambda l: l.state == 'active')
        
        if not active_limits:
            return True, ''
        
        # Check each applicable limit
        for limit in active_limits:
            available, message = limit.check_credit_availability(amount)
            if not available:
                return False, message
        
        return True, ''