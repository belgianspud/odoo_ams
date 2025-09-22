from odoo import models, fields, api, _
from odoo.exceptions import UserError

class CardVerificationWizard(models.TransientModel):
    _name = 'membership.card.verification.wizard'
    _description = 'Card Verification Wizard'

    card_number = fields.Char(
        string='Card Number',
        help="Enter the membership card number to verify"
    )
    qr_code_data = fields.Char(
        string='QR Code Data',
        help="Scan or enter QR code data for verification"
    )
    
    # Result fields
    verification_result = fields.Text(
        string='Verification Result',
        readonly=True
    )
    member_name = fields.Char(
        string='Member Name',
        readonly=True
    )
    membership_status = fields.Char(
        string='Membership Status',
        readonly=True
    )
    membership_level = fields.Char(
        string='Membership Level',
        readonly=True
    )
    expiry_date = fields.Date(
        string='Expiry Date',
        readonly=True
    )
    is_valid = fields.Boolean(
        string='Valid Card',
        readonly=True,
        default=False
    )

    def verify_card(self):
        """Verify membership card by card number"""
        if not self.card_number:
            raise UserError(_("Please enter a card number"))
        
        result = self.env['membership.membership'].verify_card(self.card_number)
        
        self._update_result_fields(result)
        
        return self._return_wizard_form()

    def verify_qr_code(self):
        """Verify membership card by QR code data"""
        if not self.qr_code_data:
            raise UserError(_("Please enter QR code data"))
        
        result = self.env['membership.membership'].verify_qr_code(self.qr_code_data)
        
        self._update_result_fields(result)
        
        return self._return_wizard_form()

    def _update_result_fields(self, result):
        """Update wizard fields based on verification result"""
        if result.get('valid'):
            self.verification_result = "Valid Card"
            self.member_name = result.get('member_name', '')
            self.membership_status = result.get('status', '')
            self.membership_level = result.get('membership_level', '')
            self.is_valid = True
            
            expiry_str = result.get('expiry_date', '')
            if expiry_str:
                try:
                    self.expiry_date = fields.Date.from_string(expiry_str)
                except (ValueError, TypeError):
                    self.expiry_date = False
        else:
            self.verification_result = f"Invalid: {result.get('message', 'Unknown error')}"
            self.member_name = False
            self.membership_status = False
            self.membership_level = False
            self.expiry_date = False
            self.is_valid = False

    def _return_wizard_form(self):
        """Return action to reload the wizard form with results"""
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'membership.card.verification.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
            'context': self.env.context,
        }

    def clear_results(self):
        """Clear verification results"""
        self.write({
            'verification_result': False,
            'member_name': False,
            'membership_status': False,
            'membership_level': False,
            'expiry_date': False,
            'is_valid': False,
        })
        return self._return_wizard_form()

    def action_view_member(self):
        """View the verified member's details"""
        if not self.is_valid or not self.member_name:
            raise UserError(_("No valid member to display"))
        
        # Find the member by name (this is not ideal but works for demo)
        partner = self.env['res.partner'].search([('name', '=', self.member_name)], limit=1)
        if not partner:
            raise UserError(_("Member record not found"))
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Member Details'),
            'res_model': 'res.partner',
            'res_id': partner.id,
            'view_mode': 'form',
            'target': 'current',
        }