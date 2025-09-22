from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import logging

_logger = logging.getLogger(__name__)


class MembershipLevelChange(models.Model):
    _name = 'membership.level.change'
    _description = 'Membership Level Change Request'
    _order = 'change_date desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    # Basic Information
    name = fields.Char(
        string='Change Reference',
        compute='_compute_name',
        store=True,
        help="Reference for this level change"
    )
    membership_id = fields.Many2one(
        'membership.membership',
        string='Membership',
        required=True,
        help="The membership being changed"
    )
    partner_id = fields.Many2one(
        'res.partner',
        related='membership_id.partner_id',
        string='Member',
        readonly=True
    )
    
    # Level Change Details
    old_level_id = fields.Many2one(
        'membership.level',
        string='From Level',
        required=True,
        help="Current membership level"
    )
    new_level_id = fields.Many2one(
        'membership.level',
        string='To Level',
        required=True,
        help="New membership level"
    )
    change_date = fields.Date(
        string='Effective Date',
        required=True,
        default=fields.Date.today,
        help="Date when the level change becomes effective"
    )
    
    # Change Type and Reason
    change_type = fields.Selection([
        ('upgrade', 'Upgrade'),
        ('downgrade', 'Downgrade'),
        ('lateral', 'Lateral Move'),
        ('correction', 'Administrative Correction')
    ], string='Change Type', compute='_compute_change_type', store=True, tracking=True)
    
    reason = fields.Selection([
        ('member_request', 'Member Request'),
        ('payment_upgrade', 'Payment for Upgrade'),
        ('promotion', 'Promotional Upgrade'),
        ('financial_hardship', 'Financial Hardship'),
        ('employment_change', 'Employment Change'),
        ('student_graduation', 'Student Graduation'),
        ('correction', 'Administrative Correction'),
        ('other', 'Other')
    ], string='Reason', required=True, tracking=True)
    
    reason_notes = fields.Text(
        string='Reason Notes',
        help="Additional details about the reason for change"
    )
    
    # Financial Calculations
    old_level_price = fields.Monetary(
        string='Old Level Price',
        related='old_level_id.price',
        currency_field='currency_id',
        readonly=True
    )
    new_level_price = fields.Monetary(
        string='New Level Price',
        related='new_level_id.price',
        currency_field='currency_id',
        readonly=True
    )
    price_difference = fields.Monetary(
        string='Price Difference',
        compute='_compute_price_difference',
        currency_field='currency_id',
        help="Difference in pricing (positive = upgrade cost, negative = downgrade credit)"
    )
    
    # Proration Calculations
    days_remaining = fields.Integer(
        string='Days Remaining',
        compute='_compute_proration',
        help="Days remaining on current membership"
    )
    proration_amount = fields.Monetary(
        string='Proration Amount',
        compute='_compute_proration',
        store=True,
        currency_field='currency_id',
        help="Prorated amount to charge/credit"
    )
    
    # Processing Information
    state = fields.Selection([
        ('draft', 'Draft'),
        ('approved', 'Approved'),
        ('processed', 'Processed'),
        ('cancelled', 'Cancelled')
    ], string='Status', default='draft', required=True, tracking=True)
    
    processed_date = fields.Datetime(
        string='Processed Date',
        help="When the level change was processed"
    )
    processed_by = fields.Many2one(
        'res.users',
        string='Processed By',
        help="User who processed the change"
    )
    
    # Related Records
    invoice_id = fields.Many2one(
        'account.move',
        string='Adjustment Invoice',
        help="Invoice created for level change adjustment"
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        default=lambda self: self.env.company.currency_id
    )

    @api.depends('partner_id.name', 'old_level_id.name', 'new_level_id.name', 'change_date')
    def _compute_name(self):
        for record in self:
            if record.partner_id and record.old_level_id and record.new_level_id:
                record.name = f"{record.partner_id.name}: {record.old_level_id.name} → {record.new_level_id.name}"
            else:
                record.name = "New Level Change"

    @api.depends('old_level_id.price', 'new_level_id.price')
    def _compute_change_type(self):
        for record in self:
            if record.old_level_id and record.new_level_id:
                old_price = record.old_level_id.price
                new_price = record.new_level_id.price
                
                if new_price > old_price:
                    record.change_type = 'upgrade'
                elif new_price < old_price:
                    record.change_type = 'downgrade'
                else:
                    record.change_type = 'lateral'
            else:
                record.change_type = 'upgrade'

    @api.depends('old_level_price', 'new_level_price')
    def _compute_price_difference(self):
        for record in self:
            record.price_difference = record.new_level_price - record.old_level_price

    @api.depends('membership_id.end_date', 'change_date', 'price_difference')
    def _compute_proration(self):
        for record in self:
            if record.membership_id.end_date and record.change_date:
                # Calculate days remaining
                remaining_days = (record.membership_id.end_date - record.change_date).days
                record.days_remaining = max(0, remaining_days)
                
                # Calculate proration
                if record.days_remaining > 0:
                    total_days = (record.membership_id.end_date - record.membership_id.start_date).days
                    if total_days > 0:
                        proration_factor = record.days_remaining / total_days
                        record.proration_amount = record.price_difference * proration_factor
                    else:
                        record.proration_amount = 0
                else:
                    record.proration_amount = 0
            else:
                record.days_remaining = 0
                record.proration_amount = 0

    @api.constrains('old_level_id', 'new_level_id')
    def _check_level_change(self):
        for record in self:
            if record.old_level_id == record.new_level_id:
                raise ValidationError(_("Old and new levels cannot be the same."))

    @api.constrains('change_date', 'membership_id')
    def _check_change_date(self):
        for record in self:
            if record.change_date and record.membership_id:
                if record.change_date < record.membership_id.start_date:
                    raise ValidationError(_("Change date cannot be before membership start date."))
                if record.change_date > record.membership_id.end_date:
                    raise ValidationError(_("Change date cannot be after membership end date."))

    @api.onchange('membership_id')
    def _onchange_membership_id(self):
        if self.membership_id and self.membership_id.level_id:
            self.old_level_id = self.membership_id.level_id

    def action_approve(self):
        """Approve the level change request"""
        for record in self:
            if record.state == 'draft':
                record.write({'state': 'approved'})
                record.message_post(body=_("Level change approved and ready for processing."))

    def action_process(self):
        """Process the approved level change"""
        for record in self:
            if record.state != 'approved':
                raise UserError(_("Only approved level changes can be processed."))
            
            # Create adjustment invoice if needed
            if record.proration_amount != 0:
                record._create_adjustment_invoice()
            
            # Update membership level
            record.membership_id.write({'level_id': record.new_level_id.id})
            
            # Update status
            record.write({
                'state': 'processed',
                'processed_date': fields.Datetime.now(),
                'processed_by': self.env.user.id
            })
            
            # Log the change
            record.membership_id.message_post(
                body=_("Membership level changed from %s to %s. Change processed by %s.") % (
                    record.old_level_id.name,
                    record.new_level_id.name,
                    self.env.user.name
                )
            )
            
            # Send notification email if configured
            record._send_level_change_notification()

    def action_cancel(self):
        """Cancel the level change request"""
        for record in self:
            if record.state == 'processed':
                raise UserError(_("Cannot cancel processed level changes."))
            
            record.write({'state': 'cancelled'})
            record.message_post(body=_("Level change request cancelled."))

    def _create_adjustment_invoice(self):
        """Create adjustment invoice for level change"""
        self.ensure_one()
        
        if self.proration_amount == 0:
            return
        
        # Determine invoice type and amount
        if self.proration_amount > 0:
            # Charge for upgrade
            invoice_type = 'out_invoice'
            amount = self.proration_amount
            description = f"Level upgrade: {self.old_level_id.name} to {self.new_level_id.name}"
        else:
            # Credit for downgrade
            invoice_type = 'out_refund'
            amount = abs(self.proration_amount)
            description = f"Level downgrade credit: {self.old_level_id.name} to {self.new_level_id.name}"
        
        # Get default account - try to get from product or use default
        account_id = False
        if self.new_level_id.product_id and self.new_level_id.product_id.categ_id:
            account_id = self.new_level_id.product_id.categ_id.property_account_income_categ_id.id
        
        if not account_id:
            # Fallback to company's default income account
            account_id = self.env.company.account_default_pos_receivable_account_id.id
        
        if not account_id:
            # Last resort - find any income account
            account = self.env['account.account'].search([
                ('account_type', '=', 'income'),
                ('company_id', '=', self.env.company.id)
            ], limit=1)
            account_id = account.id if account else False
        
        if not account_id:
            raise UserError(_("No income account configured. Please set up accounting properly."))
        
        # Create invoice
        invoice_vals = {
            'partner_id': self.partner_id.id,
            'move_type': invoice_type,
            'invoice_date': self.change_date,
            'ref': self.name,
            'membership_id': self.membership_id.id,
            'invoice_line_ids': [(0, 0, {
                'name': description,
                'quantity': 1,
                'price_unit': amount,
                'account_id': account_id,
            })]
        }
        
        invoice = self.env['account.move'].create(invoice_vals)
        self.invoice_id = invoice.id
        
        return invoice

    def _send_level_change_notification(self):
        """Send email notification about level change"""
        template = self.env.ref('ams_membership_level.email_template_level_change', False)
        if template and self.partner_id.email:
            try:
                template.send_mail(self.id, force_send=True)
            except Exception as e:
                _logger.warning(f"Failed to send level change notification: {e}")

    @api.model
    def create_level_change_request(self, membership_id, new_level_id, reason, reason_notes=None, change_date=None):
        """Helper method to create level change request"""
        membership = self.env['membership.membership'].browse(membership_id)
        
        vals = {
            'membership_id': membership_id,
            'old_level_id': membership.level_id.id,
            'new_level_id': new_level_id,
            'reason': reason,
            'reason_notes': reason_notes or '',
            'change_date': change_date or fields.Date.today()
        }
        
        return self.create(vals)


class MembershipLevelUpgradeWizard(models.TransientModel):
    _name = 'membership.level.upgrade.wizard'
    _description = 'Membership Level Change Wizard'

    membership_id = fields.Many2one(
        'membership.membership',
        string='Membership',
        required=True
    )
    current_level_id = fields.Many2one(
        'membership.level',
        string='Current Level',
        related='membership_id.level_id',
        readonly=True
    )
    new_level_id = fields.Many2one(
        'membership.level',
        string='New Level',
        required=True,
        domain="[('id', '!=', current_level_id)]"
    )
    change_date = fields.Date(
        string='Effective Date',
        required=True,
        default=fields.Date.today
    )
    reason = fields.Selection([
        ('member_request', 'Member Request'),
        ('payment_upgrade', 'Payment for Upgrade'),
        ('promotion', 'Promotional Upgrade'),
        ('financial_hardship', 'Financial Hardship'),
        ('employment_change', 'Employment Change'),
        ('student_graduation', 'Student Graduation'),
        ('correction', 'Administrative Correction'),
        ('other', 'Other')
    ], string='Reason', required=True)
    
    reason_notes = fields.Text(string='Notes')
    
    # Preview calculations
    price_difference = fields.Monetary(
        string='Price Difference',
        compute='_compute_preview',
        currency_field='currency_id'
    )
    proration_amount = fields.Monetary(
        string='Proration Amount',
        compute='_compute_preview',
        currency_field='currency_id'
    )
    currency_id = fields.Many2one(
        'res.currency',
        default=lambda self: self.env.company.currency_id
    )

    @api.depends('current_level_id', 'new_level_id', 'change_date', 'membership_id')
    def _compute_preview(self):
        for wizard in self:
            if wizard.current_level_id and wizard.new_level_id:
                wizard.price_difference = wizard.new_level_id.price - wizard.current_level_id.price
                
                # Calculate proration preview
                if wizard.membership_id.end_date and wizard.change_date:
                    remaining_days = (wizard.membership_id.end_date - wizard.change_date).days
                    if remaining_days > 0:
                        total_days = (wizard.membership_id.end_date - wizard.membership_id.start_date).days
                        if total_days > 0:
                            proration_factor = remaining_days / total_days
                            wizard.proration_amount = wizard.price_difference * proration_factor
                        else:
                            wizard.proration_amount = 0
                    else:
                        wizard.proration_amount = 0
                else:
                    wizard.proration_amount = 0
            else:
                wizard.price_difference = 0
                wizard.proration_amount = 0

    def action_create_change_request(self):
        """Create the level change request"""
        self.ensure_one()
        
        level_change = self.env['membership.level.change'].create({
            'membership_id': self.membership_id.id,
            'old_level_id': self.current_level_id.id,
            'new_level_id': self.new_level_id.id,
            'change_date': self.change_date,
            'reason': self.reason,
            'reason_notes': self.reason_notes,
        })
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Level Change Request'),
            'res_model': 'membership.level.change',
            'res_id': level_change.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_process_immediately(self):
        """Create and immediately process the level change"""
        self.ensure_one()
        
        level_change = self.env['membership.level.change'].create({
            'membership_id': self.membership_id.id,
            'old_level_id': self.current_level_id.id,
            'new_level_id': self.new_level_id.id,
            'change_date': self.change_date,
            'reason': self.reason,
            'reason_notes': self.reason_notes,
            'state': 'approved'
        })
        
        level_change.action_process()
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Level Change Processed'),
            'res_model': 'membership.level.change',
            'res_id': level_change.id,
            'view_mode': 'form',
            'target': 'current',
        }


# Add level change tracking to Membership model
class Membership(models.Model):
    _inherit = 'membership.membership'

    level_change_ids = fields.One2many(
        'membership.level.change',
        'membership_id',
        string='Level Changes'
    )
    level_change_count = fields.Integer(
        string='Level Changes',
        compute='_compute_level_change_count'
    )

    @api.depends('level_change_ids')
    def _compute_level_change_count(self):
        for membership in self:
            membership.level_change_count = len(membership.level_change_ids)

    def action_change_level(self):
        """Open level change wizard"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Change Membership Level'),
            'res_model': 'membership.level.upgrade.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_membership_id': self.id}
        }

    def action_view_level_changes(self):
        """View level change history"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Level Change History'),
            'res_model': 'membership.level.change',
            'view_mode': 'tree,form',
            'domain': [('membership_id', '=', self.id)],
            'context': {'default_membership_id': self.id}
        }