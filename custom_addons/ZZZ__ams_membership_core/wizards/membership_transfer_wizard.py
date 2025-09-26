# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from datetime import date, timedelta, datetime
import logging

_logger = logging.getLogger(__name__)


class MembershipTransferWizard(models.TransientModel):
    _name = 'ams.membership.transfer.wizard'
    _description = 'Membership Transfer Wizard'

    # Source Information
    membership_id = fields.Many2one('ams.membership', 'Membership to Transfer', 
                                   required=True, readonly=True)
    source_partner_id = fields.Many2one(related='membership_id.partner_id', 
                                        string='Current Member', readonly=True)
    product_id = fields.Many2one(related='membership_id.product_id', 
                                string='Membership Product', readonly=True)
    current_end_date = fields.Date(related='membership_id.end_date', 
                                  string='Current End Date', readonly=True)
    membership_fee = fields.Monetary(related='membership_id.membership_fee',
                                    string='Membership Fee', readonly=True)
    currency_id = fields.Many2one(related='membership_id.currency_id', readonly=True)

    # Transfer Details
    transfer_type = fields.Selection([
        ('full', 'Full Transfer'),
        ('partial', 'Partial Transfer (Split Time)'),
        ('replacement', 'Replacement Transfer'),
    ], string='Transfer Type', default='full', required=True)
    
    target_partner_id = fields.Many2one('res.partner', 'Transfer To', required=True,
                                       domain=[('is_member', '=', True)])
    
    transfer_date = fields.Date('Transfer Date', default=fields.Date.today, required=True)
    transfer_reason = fields.Selection([
        ('sale', 'Sale/Purchase'),
        ('gift', 'Gift'),
        ('company_change', 'Company Change'),
        ('family_transfer', 'Family Transfer'),
        ('error_correction', 'Error Correction'),
        ('other', 'Other'),
    ], string='Transfer Reason', required=True)
    
    # Partial Transfer Settings (for partial type)
    split_remaining_time = fields.Boolean('Split Remaining Time', 
                                         help='Split the remaining membership time between both members')
    source_end_date = fields.Date('Source New End Date',
                                 help='New end date for original member (partial transfer)')
    target_start_date = fields.Date('Target Start Date', 
                                   help='Start date for transferred membership')
    target_end_date = fields.Date('Target End Date',
                                 help='End date for transferred membership')
    
    # Financial Settings
    handle_financials = fields.Boolean('Handle Financial Adjustments', default=True)
    create_refund = fields.Boolean('Create Refund for Source', 
                                  help='Create refund for unused portion of membership')
    create_invoice = fields.Boolean('Create Invoice for Target', 
                                   help='Create invoice for new member')
    prorate_amounts = fields.Boolean('Prorate Amounts Based on Time', default=True)
    
    refund_amount = fields.Monetary('Refund Amount', currency_field='currency_id')
    invoice_amount = fields.Monetary('Invoice Amount', currency_field='currency_id')
    
    # Member Type Handling
    update_member_types = fields.Boolean('Update Member Types', default=True)
    source_new_member_type_id = fields.Many2one('ams.member.type', 'Source New Member Type',
                                               help='Change source member type after transfer')
    target_member_type_id = fields.Many2one('ams.member.type', 'Target Member Type',
                                           help='Member type for target member')
    
    # Additional Options
    terminate_source = fields.Boolean('Terminate Source Membership', 
                                     help='Terminate the original membership after transfer')
    copy_benefits = fields.Boolean('Copy Benefits to Target', default=True,
                                  help='Copy current benefits to the new membership')
    send_notifications = fields.Boolean('Send Notification Emails', default=True)
    
    # Notes and Documentation
    transfer_notes = fields.Text('Transfer Notes')
    internal_notes = fields.Text('Internal Notes')
    
    # Computed Fields
    can_transfer = fields.Boolean('Can Transfer', compute='_compute_can_transfer')
    transfer_warnings = fields.Text('Transfer Warnings', compute='_compute_transfer_warnings')
    remaining_days = fields.Integer('Remaining Days', compute='_compute_remaining_days')

    @api.depends('membership_id', 'target_partner_id', 'transfer_date')
    def _compute_can_transfer(self):
        for wizard in self:
            can_transfer = True
            
            if not wizard.membership_id:
                can_transfer = False
            elif wizard.membership_id.state not in ['active', 'grace']:
                can_transfer = False
            elif wizard.target_partner_id and wizard.target_partner_id == wizard.source_partner_id:
                can_transfer = False
            elif wizard.transfer_date and wizard.transfer_date < fields.Date.today():
                can_transfer = False
            
            wizard.can_transfer = can_transfer

    @api.depends('membership_id', 'target_partner_id', 'transfer_date')
    def _compute_transfer_warnings(self):
        for wizard in self:
            warnings = []
            
            if wizard.target_partner_id:
                # Check if target already has active membership
                existing_membership = self.env['ams.membership'].search([
                    ('partner_id', '=', wizard.target_partner_id.id),
                    ('state', '=', 'active'),
                    ('id', '!=', wizard.membership_id.id if wizard.membership_id else False)
                ])
                
                if existing_membership:
                    warnings.append(
                        f"Target member already has an active membership ({existing_membership[0].name}). "
                        "This transfer will terminate their existing membership."
                    )
                
                # Check member type compatibility
                if (wizard.membership_id and wizard.target_partner_id.member_type_id and
                    wizard.membership_id.member_type_id != wizard.target_partner_id.member_type_id):
                    warnings.append(
                        f"Target member type ({wizard.target_partner_id.member_type_id.name}) "
                        f"differs from membership type ({wizard.membership_id.member_type_id.name})."
                    )
            
            wizard.transfer_warnings = '\n'.join(warnings) if warnings else False

    @api.depends('current_end_date', 'transfer_date')
    def _compute_remaining_days(self):
        for wizard in self:
            if wizard.current_end_date and wizard.transfer_date:
                remaining = (wizard.current_end_date - wizard.transfer_date).days
                wizard.remaining_days = max(0, remaining)
            else:
                wizard.remaining_days = 0

    @api.onchange('transfer_type')
    def _onchange_transfer_type(self):
        """Update settings based on transfer type"""
        if self.transfer_type == 'full':
            self.split_remaining_time = False
            self.terminate_source = True
            self.target_start_date = self.transfer_date
            self.target_end_date = self.current_end_date
            
        elif self.transfer_type == 'partial':
            self.split_remaining_time = True
            self.terminate_source = False
            # Split the remaining time roughly in half
            if self.remaining_days > 0:
                half_days = self.remaining_days // 2
                self.source_end_date = self.transfer_date + timedelta(days=half_days)
                self.target_start_date = self.source_end_date + timedelta(days=1)
                self.target_end_date = self.current_end_date
            
        elif self.transfer_type == 'replacement':
            self.split_remaining_time = False
            self.terminate_source = True
            self.target_start_date = self.transfer_date
            self.target_end_date = self.current_end_date

    @api.onchange('prorate_amounts', 'remaining_days', 'membership_fee')
    def _onchange_financial_amounts(self):
        """Calculate prorated amounts"""
        if self.prorate_amounts and self.remaining_days > 0 and self.membership_fee:
            # Calculate daily rate
            if self.membership_id:
                total_days = (self.membership_id.end_date - self.membership_id.start_date).days
                if total_days > 0:
                    daily_rate = self.membership_fee / total_days
                    remaining_value = daily_rate * self.remaining_days
                    
                    if self.transfer_type == 'full':
                        self.refund_amount = remaining_value
                        self.invoice_amount = remaining_value
                    elif self.transfer_type == 'partial':
                        # Split the remaining value
                        if self.source_end_date and self.target_start_date:
                            source_days = (self.source_end_date - self.transfer_date).days
                            target_days = (self.target_end_date - self.target_start_date).days
                            
                            if self.remaining_days > 0:
                                self.refund_amount = (remaining_value * target_days) / self.remaining_days
                                self.invoice_amount = self.refund_amount

    def action_transfer_membership(self):
        """Execute the membership transfer"""
        self.ensure_one()
        
        if not self.can_transfer:
            raise UserError(_("This membership cannot be transferred. Please check the warnings."))
        
        try:
            # Start transaction
            with self.env.cr.savepoint():
                if self.transfer_type == 'full':
                    self._process_full_transfer()
                elif self.transfer_type == 'partial':
                    self._process_partial_transfer()
                elif self.transfer_type == 'replacement':
                    self._process_replacement_transfer()
                
                # Handle financial adjustments
                if self.handle_financials:
                    self._process_financial_adjustments()
                
                # Handle member type updates
                if self.update_member_types:
                    self._update_member_types()
                
                # Send notifications
                if self.send_notifications:
                    self._send_transfer_notifications()
                
                # Log the transfer
                self._log_transfer()
                
        except Exception as e:
            _logger.error(f"Membership transfer failed: {str(e)}")
            raise UserError(f"Transfer failed: {str(e)}")
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Transfer Complete'),
                'message': _('Membership has been successfully transferred.'),
                'type': 'success'
            }
        }

    def _process_full_transfer(self):
        """Process full membership transfer"""
        # Terminate existing membership for target if exists
        existing = self.env['ams.membership'].search([
            ('partner_id', '=', self.target_partner_id.id),
            ('state', '=', 'active')
        ])
        existing.write({'state': 'terminated', 'notes': 'Terminated due to membership transfer'})
        
        # Transfer the membership
        self.membership_id.write({
            'partner_id': self.target_partner_id.id,
            'start_date': self.target_start_date,
            'end_date': self.target_end_date,
            'notes': f"Transferred from {self.source_partner_id.name} on {self.transfer_date}"
        })
        
        # Update source member status if terminating
        if self.terminate_source:
            self.source_partner_id.write({'member_status': 'lapsed'})

    def _process_partial_transfer(self):
        """Process partial membership transfer"""
        # Update original membership end date
        self.membership_id.write({
            'end_date': self.source_end_date,
            'notes': f"Partially transferred to {self.target_partner_id.name} on {self.transfer_date}"
        })
        
        # Create new membership for target
        new_membership_vals = {
            'partner_id': self.target_partner_id.id,
            'product_id': self.product_id.id,
            'start_date': self.target_start_date,
            'end_date': self.target_end_date,
            'membership_fee': self.invoice_amount or self.membership_fee,
            'state': 'active',
            'notes': f"Transferred from {self.source_partner_id.name} on {self.transfer_date}"
        }
        
        if self.copy_benefits:
            new_membership_vals['benefit_ids'] = [(6, 0, self.membership_id.benefit_ids.ids)]
        
        new_membership = self.env['ams.membership'].create(new_membership_vals)
        
        return new_membership

    def _process_replacement_transfer(self):
        """Process replacement transfer"""
        # Same as full transfer but with different documentation
        self._process_full_transfer()

    def _process_financial_adjustments(self):
        """Handle refunds and invoices"""
        if self.create_refund and self.refund_amount > 0:
            # Create refund for source member
            # This would integrate with accounting module
            _logger.info(f"Refund of {self.refund_amount} should be created for {self.source_partner_id.name}")
        
        if self.create_invoice and self.invoice_amount > 0:
            # Create invoice for target member
            # This would integrate with accounting module
            _logger.info(f"Invoice of {self.invoice_amount} should be created for {self.target_partner_id.name}")

    def _update_member_types(self):
        """Update member types as needed"""
        if self.source_new_member_type_id:
            self.source_partner_id.write({'member_type_id': self.source_new_member_type_id.id})
        
        if self.target_member_type_id:
            self.target_partner_id.write({'member_type_id': self.target_member_type_id.id})

    def _send_transfer_notifications(self):
        """Send notification emails"""
        # This would send emails to both members about the transfer
        # Implementation would depend on email template system
        _logger.info(f"Transfer notifications should be sent to both {self.source_partner_id.name} and {self.target_partner_id.name}")

    def _log_transfer(self):
        """Log the transfer in both member records"""
        transfer_note = f"Membership transfer completed on {fields.Date.today()}\n"
        transfer_note += f"Type: {dict(self._fields['transfer_type'].selection)[self.transfer_type]}\n"
        transfer_note += f"Reason: {dict(self._fields['transfer_reason'].selection)[self.transfer_reason]}\n"
        
        if self.transfer_notes:
            transfer_note += f"Notes: {self.transfer_notes}\n"
        
        # Log on source member
        self.source_partner_id.message_post(
            body=f"Membership transferred TO {self.target_partner_id.name}<br/>{transfer_note}",
            message_type='notification'
        )
        
        # Log on target member
        self.target_partner_id.message_post(
            body=f"Membership transferred FROM {self.source_partner_id.name}<br/>{transfer_note}",
            message_type='notification'
        )

    # Constraints
    @api.constrains('transfer_date')
    def _check_transfer_date(self):
        for wizard in self:
            if wizard.transfer_date < fields.Date.today():
                raise ValidationError(_("Transfer date cannot be in the past."))

    @api.constrains('source_end_date', 'target_start_date', 'target_end_date')
    def _check_partial_dates(self):
        for wizard in self:
            if wizard.transfer_type == 'partial':
                if not wizard.source_end_date or not wizard.target_start_date or not wizard.target_end_date:
                    raise ValidationError(_("All dates must be set for partial transfers."))
                
                if wizard.source_end_date <= wizard.transfer_date:
                    raise ValidationError(_("Source end date must be after transfer date."))
                
                if wizard.target_start_date <= wizard.transfer_date:
                    raise ValidationError(_("Target start date must be after transfer date."))
                
                if wizard.target_end_date <= wizard.target_start_date:
                    raise ValidationError(_("Target end date must be after target start date."))

    @api.constrains('target_partner_id', 'source_partner_id')
    def _check_different_partners(self):
        for wizard in self:
            if wizard.target_partner_id == wizard.source_partner_id:
                raise ValidationError(_("Cannot transfer membership to the same member."))

    @api.model
    def default_get(self, fields_list):
        """Set defaults based on context"""
        res = super().default_get(fields_list)
        
        # Get membership from context
        if self.env.context.get('active_model') == 'ams.membership':
            membership_id = self.env.context.get('active_id')
            if membership_id:
                res['membership_id'] = membership_id
        
        return res