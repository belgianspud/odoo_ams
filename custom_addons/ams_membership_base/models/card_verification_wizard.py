from odoo import models, fields, api, _
from odoo.exceptions import UserError

class CardVerificationWizard(models.TransientModel):
    _name = 'membership.card.verification.wizard'
    _description = 'Card Verification Wizard'

    card_number = fields.Char(string='Card Number')
    qr_code_data = fields.Char(string='QR Code Data')
    
    # Result fields
    verification_result = fields.Text(string='Result', readonly=True)
    member_name = fields.Char(string='Member Name', readonly=True)
    membership_status = fields.Char(string='Status', readonly=True)
    expiry_date = fields.Date(string='Expiry Date', readonly=True)

    def verify_card(self):
        if not self.card_number:
            raise UserError(_("Please enter a card number"))
        
        result = self.env['membership.membership'].verify_card(self.card_number)
        
        if result['valid']:
            self.verification_result = "✅ Valid Card"
            self.member_name = result.get('member_name', '')
            self.membership_status = result.get('status', '')
            expiry_str = result.get('expiry_date', '')
            if expiry_str:
                try:
                    self.expiry_date = fields.Date.from_string(expiry_str)
                except:
                    pass
        else:
            self.verification_result = f"❌ Invalid: {result['message']}"
            self.member_name = False
            self.membership_status = False
            self.expiry_date = False
        
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'membership.card.verification.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def verify_qr_code(self):
        if not self.qr_code_data:
            raise UserError(_("Please enter QR code data"))
        
        result = self.env['membership.membership'].verify_qr_code(self.qr_code_data)
        
        if result['valid']:
            self.verification_result = "✅ Valid QR Code"
            self.member_name = result.get('member_name', '')
            self.membership_status = result.get('status', '')
            expiry_str = result.get('expiry_date', '')
            if expiry_str:
                try:
                    self.expiry_date = fields.Date.from_string(expiry_str)
                except:
                    pass
        else:
            self.verification_result = f"❌ Invalid: {result['message']}"
            self.member_name = False
            self.membership_status = False
            self.expiry_date = False
        
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'membership.card.verification.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }