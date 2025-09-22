from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import base64
import qrcode
from io import BytesIO
import logging

_logger = logging.getLogger(__name__)


class Membership(models.Model):
    _inherit = 'membership.membership'

    # Card Information
    card_number = fields.Char(
        string='Card Number',
        compute='_compute_card_number',
        store=True,
        help="Unique membership card number"
    )
    card_issued_date = fields.Date(
        string='Card Issued Date',
        help="Date when membership card was issued"
    )
    card_expiry_date = fields.Date(
        string='Card Expiry Date',
        related='end_date',
        help="Date when membership card expires"
    )
    
    # Digital Card
    qr_code = fields.Binary(
        string='QR Code',
        compute='_compute_qr_code',
        help="QR code for digital membership verification"
    )
    digital_card_url = fields.Char(
        string='Digital Card URL',
        compute='_compute_digital_card_url',
        help="URL for digital membership card"
    )
    
    # Card Status
    card_status = fields.Selection([
        ('active', 'Active'),
        ('expired', 'Expired'),
        ('suspended', 'Suspended'),
        ('replaced', 'Replaced')
    ], string='Card Status', compute='_compute_card_status', store=True)
    
    # Card Design Options
    card_template = fields.Selection([
        ('standard', 'Standard'),
        ('premium', 'Premium'),
        ('custom', 'Custom')
    ], string='Card Template', default='standard')
    
    @api.depends('id', 'partner_id.id')
    def _compute_card_number(self):
        for membership in self:
            if membership.id and membership.partner_id:
                # Generate card number: YEAR + MEMBER_ID + MEMBERSHIP_ID
                year = str(fields.Date.today().year)
                member_id = str(membership.partner_id.id).zfill(6)
                membership_id = str(membership.id).zfill(4)
                membership.card_number = f"{year}{member_id}{membership_id}"
            else:
                membership.card_number = False
    
    @api.depends('card_number', 'partner_id.name', 'level_id.name', 'end_date')
    def _compute_qr_code(self):
        for membership in self:
            if membership.card_number:
                # Create QR code data
                qr_data = {
                    'card_number': membership.card_number,
                    'member_name': membership.partner_id.name,
                    'member_id': membership.partner_id.id,
                    'membership_level': membership.level_id.name if membership.level_id else '',
                    'expiry_date': membership.end_date.isoformat() if membership.end_date else '',
                    'verification_url': membership.digital_card_url or ''
                }
                
                # Generate QR code
                qr_text = f"MEMBER:{membership.card_number}|{membership.partner_id.name}|{membership.end_date}"
                
                qr = qrcode.QRCode(
                    version=1,
                    error_correction=qrcode.constants.ERROR_CORRECT_L,
                    box_size=10,
                    border=4,
                )
                qr.add_data(qr_text)
                qr.make(fit=True)
                
                # Create QR code image
                qr_image = qr.make_image(fill_color="black", back_color="white")
                
                # Convert to base64
                buffer = BytesIO()
                qr_image.save(buffer, format='PNG')
                qr_code_data = base64.b64encode(buffer.getvalue())
                
                membership.qr_code = qr_code_data
            else:
                membership.qr_code = False
    
    @api.depends('card_number')
    def _compute_digital_card_url(self):
        for membership in self:
            if membership.card_number:
                base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
                membership.digital_card_url = f"{base_url}/membership/card/{membership.card_number}"
            else:
                membership.digital_card_url = False
    
    @api.depends('state', 'end_date')
    def _compute_card_status(self):
        today = fields.Date.today()
        for membership in self:
            if membership.state == 'cancelled':
                membership.card_status = 'suspended'
            elif membership.end_date and membership.end_date < today:
                membership.card_status = 'expired'
            elif membership.state == 'active':
                membership.card_status = 'active'
            else:
                membership.card_status = 'expired'
    
    def action_issue_card(self):
        """Issue a new membership card"""
        self.ensure_one()
        self.card_issued_date = fields.Date.today()
        self._compute_qr_code()  # Regenerate QR code
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Membership Card'),
            'res_model': 'membership.membership',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }
    
    def action_generate_digital_card(self):
        """Generate and download digital membership card"""
        self.ensure_one()
        
        # Generate PDF card
        report = self.env.ref('membership_base.report_membership_card')
        return report.report_action(self)
    
    def action_send_digital_card(self):
        """Send digital card via email"""
        self.ensure_one()
        
        template = self.env.ref('membership_base.email_template_digital_card', False)
        if template:
            template.send_mail(self.id, force_send=True)
            
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': _('Digital membership card sent to %s') % self.partner_id.email,
                'type': 'success',
            }
        }
    
    def verify_card(self, card_number):
        """Verify membership card by card number"""
        membership = self.search([('card_number', '=', card_number)], limit=1)
        
        if not membership:
            return {'valid': False, 'message': 'Card not found'}
        
        if membership.card_status != 'active':
            return {'valid': False, 'message': f'Card status: {membership.card_status}'}
        
        today = fields.Date.today()
        if membership.end_date and membership.end_date < today:
            return {'valid': False, 'message': 'Card expired'}
        
        return {
            'valid': True,
            'member_name': membership.partner_id.name,
            'membership_level': membership.level_id.name if membership.level_id else '',
            'expiry_date': membership.end_date,
            'chapter': membership.chapter_id.name if membership.chapter_id else ''
        }


class MembershipCardTemplate(models.Model):
    _name = 'membership.card.template'
    _description = 'Membership Card Template'

    name = fields.Char(
        string='Template Name',
        required=True,
        help="Name of the card template"
    )
    description = fields.Text(
        string='Description',
        help="Description of the template"
    )
    
    # Design Elements
    background_color = fields.Char(
        string='Background Color',
        default='#FFFFFF',
        help="Hex color code for card background"
    )
    text_color = fields.Char(
        string='Text Color',
        default='#000000',
        help="Hex color code for text"
    )
    logo_position = fields.Selection([
        ('top-left', 'Top Left'),
        ('top-center', 'Top Center'),
        ('top-right', 'Top Right'),
        ('center', 'Center')
    ], string='Logo Position', default='top-left')
    
    # Template File
    template_file = fields.Binary(
        string='Template File',
        help="Template file for card design"
    )
    template_filename = fields.Char(
        string='Template Filename'
    )
    
    # Usage
    is_default = fields.Boolean(
        string='Default Template',
        help="Use as default template for new cards"
    )
    active = fields.Boolean(
        string='Active',
        default=True,
        help="Template is available for use"
    )
    
    @api.constrains('is_default')
    def _check_single_default(self):
        if self.is_default:
            others = self.search([('is_default', '=', True), ('id', '!=', self.id)])
            if others:
                raise ValidationError(_("Only one template can be set as default."))