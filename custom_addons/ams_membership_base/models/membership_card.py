from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
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
        store=False,  # Don't store to avoid large binary data in database
        help="QR code for digital membership verification"
    )
    qr_code_data = fields.Char(
        string='QR Code Data',
        compute='_compute_qr_code_data',
        store=True,
        help="Data encoded in QR code"
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
    
    @api.depends('id', 'partner_id.id', 'start_date')
    def _compute_card_number(self):
        for membership in self:
            if membership.id and membership.partner_id and membership.start_date:
                # Generate card number: YEAR + MEMBER_ID + MEMBERSHIP_ID
                year = str(membership.start_date.year)
                member_id = str(membership.partner_id.id).zfill(6)
                membership_id = str(membership.id).zfill(4)
                membership.card_number = f"{year}{member_id}{membership_id}"
            else:
                membership.card_number = False
    
    @api.depends('card_number', 'partner_id.name', 'end_date', 'state')
    def _compute_qr_code_data(self):
        for membership in self:
            if membership.card_number and membership.partner_id:
                # Create QR code data with verification info
                qr_data = f"MEMBER:{membership.card_number}|{membership.partner_id.name}|{membership.end_date or ''}|{membership.state}|{membership.id}"
                membership.qr_code_data = qr_data
            else:
                membership.qr_code_data = False
    
    @api.depends('qr_code_data')
    def _compute_qr_code(self):
        for membership in self:
            if membership.qr_code_data:
                try:
                    # Generate QR code
                    qr = qrcode.QRCode(
                        version=1,
                        error_correction=qrcode.constants.ERROR_CORRECT_M,
                        box_size=10,
                        border=4,
                    )
                    qr.add_data(membership.qr_code_data)
                    qr.make(fit=True)
                    
                    # Create QR code image
                    qr_image = qr.make_image(fill_color="black", back_color="white")
                    
                    # Convert to base64
                    buffer = BytesIO()
                    qr_image.save(buffer, format='PNG')
                    qr_code_data = base64.b64encode(buffer.getvalue())
                    
                    membership.qr_code = qr_code_data
                except Exception as e:
                    _logger.error(f"Error generating QR code for membership {membership.id}: {str(e)}")
                    membership.qr_code = False
            else:
                membership.qr_code = False
    
    @api.depends('card_number')
    def _compute_digital_card_url(self):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url', '')
        for membership in self:
            if membership.card_number and base_url:
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
        # Force recomputation of QR code
        self._compute_qr_code()
        
        self.message_post(body=_("Membership card issued"))
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Membership Card'),
            'res_model': 'membership.membership',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'current',
        }
    
    def action_generate_digital_card(self):
        """Generate and download digital membership card"""
        self.ensure_one()
        
        if not self.card_number:
            raise UserError(_("Card number must be generated before creating digital card."))
        
        # Generate PDF card
        try:
            report = self.env.ref('ams_membership_base.report_membership_card')
            return report.report_action(self)
        except Exception as e:
            raise UserError(_("Error generating digital card: %s") % str(e))
    
    def action_send_digital_card(self):
        """Send digital card via email"""
        self.ensure_one()
        
        if not self.partner_id.email:
            raise UserError(_("No email address found for member %s") % self.partner_id.name)
        
        template = self.env.ref('ams_membership_base.email_template_digital_card', raise_if_not_found=False)
        if template:
            try:
                template.send_mail(self.id, force_send=True)
                self.message_post(body=_("Digital membership card sent to %s") % self.partner_id.email)
                
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'message': _('Digital membership card sent to %s') % self.partner_id.email,
                        'type': 'success',
                    }
                }
            except Exception as e:
                _logger.error(f"Error sending digital card email: {str(e)}")
                raise UserError(_("Error sending email: %s") % str(e))
        else:
            raise UserError(_("Email template not found. Please contact administrator."))
    
    @api.model
    def verify_card(self, card_number):
        """Verify membership card by card number"""
        if not card_number:
            return {'valid': False, 'message': 'Invalid card number format'}
        
        membership = self.search([('card_number', '=', card_number)], limit=1)
        
        if not membership:
            return {'valid': False, 'message': 'Card not found'}
        
        if membership.card_status != 'active':
            return {
                'valid': False, 
                'message': f'Card status: {dict(membership._fields["card_status"].selection)[membership.card_status]}'
            }
        
        today = fields.Date.today()
        if membership.end_date and membership.end_date < today:
            return {'valid': False, 'message': 'Card expired'}
        
        return {
            'valid': True,
            'member_name': membership.partner_id.name,
            'member_id': membership.partner_id.id,
            'membership_level': getattr(membership, 'level_id', False) and membership.level_id.name or '',
            'expiry_date': membership.end_date and membership.end_date.strftime('%Y-%m-%d') or '',
            'chapter': getattr(membership, 'chapter_id', False) and membership.chapter_id.name or '',
            'status': membership.state
        }
    
    @api.model
    def verify_qr_code(self, qr_data):
        """Verify membership using QR code data"""
        try:
            if not qr_data or not qr_data.startswith('MEMBER:'):
                return {'valid': False, 'message': 'Invalid QR code format'}
            
            # Parse QR code data
            parts = qr_data.replace('MEMBER:', '').split('|')
            if len(parts) < 5:
                return {'valid': False, 'message': 'Invalid QR code data'}
            
            card_number, member_name, expiry_date, state, membership_id = parts[:5]
            
            # Verify membership exists and data matches
            membership = self.browse(int(membership_id))
            if not membership.exists():
                return {'valid': False, 'message': 'Membership not found'}
            
            if membership.card_number != card_number:
                return {'valid': False, 'message': 'Card number mismatch'}
            
            # Use the existing verify_card method
            return self.verify_card(card_number)
            
        except (ValueError, IndexError) as e:
            _logger.warning(f"QR code verification error: {str(e)}")
            return {'valid': False, 'message': 'Invalid QR code format'}


class MembershipCardTemplate(models.Model):
    _name = 'membership.card.template'
    _description = 'Membership Card Template'
    _order = 'sequence, name'

    name = fields.Char(
        string='Template Name',
        required=True,
        help="Name of the card template"
    )
    description = fields.Text(
        string='Description',
        help="Description of the template"
    )
    sequence = fields.Integer(
        string='Sequence',
        default=10,
        help="Order of display"
    )
    active = fields.Boolean(
        string='Active',
        default=True,
        help="Template is available for use"
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
    accent_color = fields.Char(
        string='Accent Color',
        default='#007bff',
        help="Hex color code for accents and highlights"
    )
    logo_position = fields.Selection([
        ('top-left', 'Top Left'),
        ('top-center', 'Top Center'),
        ('top-right', 'Top Right'),
        ('center', 'Center')
    ], string='Logo Position', default='top-left')
    
    # Template Configuration
    show_qr_code = fields.Boolean(
        string='Show QR Code',
        default=True,
        help="Include QR code on card"
    )
    show_member_photo = fields.Boolean(
        string='Show Member Photo',
        default=False,
        help="Include member photo on card"
    )
    
    # Template File
    template_file = fields.Binary(
        string='Template File',
        help="Template file for card design"
    )
    template_filename = fields.Char(
        string='Template Filename'
    )
    
    # Usage Tracking
    is_default = fields.Boolean(
        string='Default Template',
        help="Use as default template for new cards"
    )
    usage_count = fields.Integer(
        string='Usage Count',
        default=0,
        help="Number of cards generated with this template"
    )
    
    @api.constrains('is_default')
    def _check_single_default(self):
        if self.is_default:
            other_defaults = self.search([
                ('is_default', '=', True), 
                ('id', '!=', self.id),
                ('active', '=', True)
            ])
            if other_defaults:
                raise ValidationError(_("Only one template can be set as default."))
    
    @api.constrains('background_color', 'text_color', 'accent_color')
    def _check_color_format(self):
        import re
        color_pattern = r'^#[0-9A-Fa-f]{6}$'
        
        for template in self:
            if template.background_color and not re.match(color_pattern, template.background_color):
                raise ValidationError(_("Background color must be in hex format (#RRGGBB)"))
            if template.text_color and not re.match(color_pattern, template.text_color):
                raise ValidationError(_("Text color must be in hex format (#RRGGBB)"))
            if template.accent_color and not re.match(color_pattern, template.accent_color):
                raise ValidationError(_("Accent color must be in hex format (#RRGGBB)"))
    
    def increment_usage(self):
        """Increment usage counter when template is used"""
        self.usage_count += 1