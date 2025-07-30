from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
import logging

_logger = logging.getLogger(__name__)


class SubscriptionScheduledChange(models.Model):
    """Model for scheduled subscription changes"""
    _name = 'ams.subscription.scheduled.change'
    _description = 'Scheduled Subscription Change'
    _order = 'effective_date, id'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    subscription_id = fields.Many2one(
        'ams.member.subscription',
        string='Subscription',
        required=True,
        ondelete='cascade',
        tracking=True
    )
    
    partner_id = fields.Many2one(
        'res.partner',
        string='Member',
        related='subscription_id.partner_id',
        store=True,
        readonly=True
    )
    
    target_membership_type_id = fields.Many2one(
        'ams.membership.type',
        string='Target Membership Type',
        required=True,
        tracking=True
    )
    
    current_membership_type_id = fields.Many2one(
        'ams.membership.type',
        string='Current Membership Type',
        related='subscription_id.membership_type_id',
        store=True,
        readonly=True
    )
    
    effective_date = fields.Date(
        string='Effective Date',
        required=True,
        tracking=True
    )
    
    change_type = fields.Selection([
        ('upgrade', 'Upgrade'),
        ('downgrade', 'Downgrade'),
        ('lateral', 'Lateral Change')
    ], string='Change Type', required=True, tracking=True)
    
    financial_adjustment = fields.Float(
        string='Financial Adjustment',
        digits='Product Price',
        help="Amount to charge or refund"
    )
    
    state = fields.Selection([
        ('scheduled', 'Scheduled'),
        ('processed', 'Processed'),
        ('cancelled', 'Cancelled'),
        ('failed', 'Failed')
    ], string='Status', default='scheduled', required=True, tracking=True)
    
    notes = fields.Html(
        string='Notes',
        help="Additional notes about the scheduled change"
    )
    
    processed_date = fields.Date(
        string='Processed Date',
        readonly=True
    )
    
    processed_by = fields.Many2one(
        'res.users',
        string='Processed By',
        readonly=True
    )
    
    error_message = fields.Text(
        string='Error Message',
        readonly=True,
        help="Error message if processing failed"
    )
    
    created_by = fields.Many2one(
        'res.users',
        string='Created By',
        default=lambda self: self.env.user,
        readonly=True
    )

    @api.model
    def process_scheduled_changes(self):
        """Cron job to process scheduled changes"""
        today = fields.Date.today()
        
        scheduled_changes = self.search([
            ('state', '=', 'scheduled'),
            ('effective_date', '<=', today)
        ])
        
        processed_count = 0
        failed_count = 0
        
        for change in scheduled_changes:
            try:
                change._execute_change()
                change.write({
                    'state': 'processed',
                    'processed_date': today,
                    'processed_by': self.env.user.id
                })
                processed_count += 1
                
                # Log success
                change.message_post(
                    body=_("Scheduled change processed successfully")
                )
                
            except Exception as e:
                change.write({
                    'state': 'failed',
                    'error_message': str(e),
                    'processed_date': today,
                    'processed_by': self.env.user.id
                })
                failed_count += 1
                
                # Log error
                change.message_post(
                    body=_("Scheduled change failed: %s") % str(e)
                )
                _logger.error(f"Failed to process scheduled change {change.id}: {e}")
        
        if scheduled_changes:
            _logger.info(f"Processed scheduled changes: {processed_count} successful, {failed_count} failed")
        
        return {
            'processed': processed_count,
            'failed': failed_count
        }

    def _execute_change(self):
        """Execute the scheduled change"""
        self.ensure_one()
        
        if self.state != 'scheduled':
            raise ValidationError(_("Only scheduled changes can be executed"))
        
        if not self.subscription_id.exists():
            raise ValidationError(_("Related subscription no longer exists"))
        
        if self.subscription_id.state not in ['active', 'pending_renewal']:
            raise ValidationError(_("Subscription is not in a valid state for changes"))
        
        # Update subscription
        self.subscription_id.write({
            'membership_type_id': self.target_membership_type_id.id,
            'unit_price': self.target_membership_type_id.price,
        })
        
        # Handle financial adjustment if needed
        if self.financial_adjustment != 0:
            self._create_financial_adjustment()
        
        # Log the change on subscription
        self.subscription_id.message_post(
            body=_("Scheduled membership %s processed: %s → %s") % (
                self.change_type,
                self.current_membership_type_id.name,
                self.target_membership_type_id.name
            )
        )

    def _create_financial_adjustment(self):
        """Create financial adjustment for the change"""
        if self.financial_adjustment == 0:
            return
        
        # Create invoice or credit note based on adjustment amount
        if self.financial_adjustment > 0:
            # Create invoice for additional charges
            invoice_vals = {
                'partner_id': self.partner_id.id,
                'move_type': 'out_invoice',
                'subscription_id': self.subscription_id.id,
                'invoice_line_ids': [(0, 0, {
                    'name': f"Membership {self.change_type.title()}: {self.current_membership_type_id.name} → {self.target_membership_type_id.name}",
                    'quantity': 1,
                    'price_unit': self.financial_adjustment,
                    'account_id': self._get_income_account().id,
                })]
            }
            
            self.env['account.move'].create(invoice_vals)
            
        else:
            # Create credit note for refund
            credit_vals = {
                'partner_id': self.partner_id.id,
                'move_type': 'out_refund',
                'subscription_id': self.subscription_id.id,
                'invoice_line_ids': [(0, 0, {
                    'name': f"Membership {self.change_type.title()} Refund: {self.current_membership_type_id.name} → {self.target_membership_type_id.name}",
                    'quantity': 1,
                    'price_unit': abs(self.financial_adjustment),
                    'account_id': self._get_income_account().id,
                })]
            }
            
            self.env['account.move'].create(credit_vals)

    def _get_income_account(self):
        """Get appropriate income account"""
        account = self.env['account.account'].search([
            ('code', 'like', '4%'),
            ('company_id', '=', self.env.company.id)
        ], limit=1)
        
        if not account:
            raise ValidationError(_("No income account found. Please configure your chart of accounts."))
        
        return account

    def action_cancel_change(self):
        """Cancel the scheduled change"""
        for record in self:
            if record.state != 'scheduled':
                raise UserError(_("Only scheduled changes can be cancelled"))
            
            record.write({
                'state': 'cancelled',
                'processed_date': fields.Date.today(),
                'processed_by': self.env.user.id
            })
            
            record.message_post(
                body=_("Scheduled change cancelled by %s") % self.env.user.name
            )

    def action_reschedule(self):
        """Reschedule the change to a new date"""
        self.ensure_one()
        
        if self.state != 'scheduled':
            raise UserError(_("Only scheduled changes can be rescheduled"))
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Reschedule Change'),
            'res_model': 'ams.subscription.scheduled.change',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
            'context': {'reschedule_mode': True}
        }

    def action_execute_now(self):
        """Execute the scheduled change immediately"""
        self.ensure_one()
        
        if self.state != 'scheduled':
            raise UserError(_("Only scheduled changes can be executed"))
        
        try:
            self._execute_change()
            self.write({
                'state': 'processed',
                'processed_date': fields.Date.today(),
                'processed_by': self.env.user.id,
                'effective_date': fields.Date.today()
            })
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Success'),
                    'message': _('Scheduled change executed successfully'),
                    'type': 'success'
                }
            }
            
        except Exception as e:
            self.write({
                'state': 'failed',
                'error_message': str(e),
                'processed_date': fields.Date.today(),
                'processed_by': self.env.user.id
            })
            
            raise UserError(_("Failed to execute change: %s") % str(e))