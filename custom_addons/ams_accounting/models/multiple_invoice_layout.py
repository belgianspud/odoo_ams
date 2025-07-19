from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import logging

_logger = logging.getLogger(__name__)


class MultipleInvoiceLayout(models.Model):
    """
    Invoice layout templates for different types of AMS invoices
    """
    _name = 'multiple.invoice.layout'
    _description = 'Multiple Invoice Layout'
    _order = 'sequence, name'
    
    # ========================
    # BASIC INFORMATION
    # ========================
    
    name = fields.Char('Layout Name', required=True, translate=True)
    description = fields.Text('Description', translate=True)
    sequence = fields.Integer('Sequence', default=10)
    active = fields.Boolean('Active', default=True)
    
    # Layout Type
    layout_type = fields.Selection([
        ('membership', 'Membership Invoice'),
        ('renewal', 'Renewal Invoice'),
        ('chapter', 'Chapter Fee Invoice'),
        ('donation', 'Donation Receipt'),
        ('event', 'Event Registration'),
        ('publication', 'Publication Invoice'),
        ('late_fee', 'Late Fee Notice'),
        ('statement', 'Financial Statement'),
        ('custom', 'Custom Layout')
    ], string='Layout Type', required=True, default='membership')
    
    # ========================
    # LAYOUT CONFIGURATION
    # ========================
    
    # Header Configuration
    show_company_logo = fields.Boolean('Show Company Logo', default=True)
    logo_position = fields.Selection([
        ('left', 'Left'),
        ('center', 'Center'),
        ('right', 'Right')
    ], string='Logo Position', default='left')
    
    custom_header_text = fields.Html('Custom Header Text',
        help="Additional text to display in the invoice header")
    
    show_member_number = fields.Boolean('Show Member Number', default=True)
    show_subscription_details = fields.Boolean('Show Subscription Details', default=True)
    
    # Invoice Title and Reference
    invoice_title = fields.Char('Invoice Title', translate=True,
        help="Custom title for the invoice (e.g., 'Membership Invoice', 'Annual Billing')")
    
    reference_format = fields.Char('Reference Format', default='INV-{year}-{sequence}',
        help="Format for invoice reference. Available variables: {year}, {month}, {sequence}, {member_number}")
    
    # ========================
    # CONTENT CONFIGURATION
    # ========================
    
    # Line Item Display
    show_product_code = fields.Boolean('Show Product Code', default=False)
    show_product_description = fields.Boolean('Show Product Description', default=True)
    product_description_template = fields.Text('Product Description Template',
        help="Template for product description. Available variables: {product_name}, {period_start}, {period_end}")
    
    show_unit_price = fields.Boolean('Show Unit Price', default=True)
    show_quantity = fields.Boolean('Show Quantity', default=True)
    show_discount = fields.Boolean('Show Discount', default=False)
    show_taxes = fields.Boolean('Show Taxes', default=True)
    
    # Grouping and Sorting
    group_by_subscription_type = fields.Boolean('Group by Subscription Type', default=False)
    group_by_chapter = fields.Boolean('Group by Chapter', default=False)
    sort_lines_by = fields.Selection([
        ('sequence', 'Sequence'),
        ('product_name', 'Product Name'),
        ('amount', 'Amount'),
        ('subscription_type', 'Subscription Type')
    ], string='Sort Lines By', default='sequence')
    
    # ========================
    # MEMBER INFORMATION
    # ========================
    
    # Member Details Display
    show_member_type = fields.Boolean('Show Member Type', default=True)
    show_member_since = fields.Boolean('Show Member Since', default=True)
    show_membership_status = fields.Boolean('Show Membership Status', default=True)
    show_chapter_affiliation = fields.Boolean('Show Chapter Affiliation', default=True)
    
    # Contact Information
    show_member_address = fields.Boolean('Show Member Address', default=True)
    show_member_phone = fields.Boolean('Show Member Phone', default=False)
    show_member_email = fields.Boolean('Show Member Email', default=False)
    
    # ========================
    # FINANCIAL INFORMATION
    # ========================
    
    # Payment Information
    show_payment_terms = fields.Boolean('Show Payment Terms', default=True)
    show_due_date = fields.Boolean('Show Due Date', default=True)
    show_payment_methods = fields.Boolean('Show Payment Methods', default=True)
    
    payment_instructions = fields.Html('Payment Instructions',
        help="Custom payment instructions to display on invoice")
    
    # Total Display
    show_subtotal = fields.Boolean('Show Subtotal', default=True)
    show_tax_breakdown = fields.Boolean('Show Tax Breakdown', default=True)
    show_total_due = fields.Boolean('Show Total Due', default=True)
    show_amount_paid = fields.Boolean('Show Amount Paid', default=False)
    show_balance_due = fields.Boolean('Show Balance Due', default=True)
    
    # Currency and Formatting
    currency_position = fields.Selection([
        ('before', 'Before Amount'),
        ('after', 'After Amount')
    ], string='Currency Position', default='before')
    
    number_format = fields.Selection([
        ('standard', 'Standard (1,234.56)'),
        ('european', 'European (1.234,56)'),
        ('compact', 'Compact (1234.56)')
    ], string='Number Format', default='standard')
    
    # ========================
    # FOOTER CONFIGURATION
    # ========================
    
    # Footer Content
    show_company_details = fields.Boolean('Show Company Details', default=True)
    show_tax_info = fields.Boolean('Show Tax Information', default=True)
    show_bank_details = fields.Boolean('Show Bank Details', default=False)
    
    custom_footer_text = fields.Html('Custom Footer Text',
        help="Additional text to display in the invoice footer")
    
    # Legal and Compliance
    show_terms_conditions = fields.Boolean('Show Terms & Conditions', default=False)
    terms_conditions_text = fields.Html('Terms & Conditions Text')
    
    show_privacy_notice = fields.Boolean('Show Privacy Notice', default=False)
    privacy_notice_text = fields.Html('Privacy Notice Text')
    
    # ========================
    # STYLING AND APPEARANCE
    # ========================
    
    # Color Scheme
    primary_color = fields.Char('Primary Color', default='#1f2937',
        help="Hex color code for primary elements")
    secondary_color = fields.Char('Secondary Color', default='#6b7280',
        help="Hex color code for secondary elements")
    accent_color = fields.Char('Accent Color', default='#3b82f6',
        help="Hex color code for accent elements")
    
    # Typography
    font_family = fields.Selection([
        ('helvetica', 'Helvetica'),
        ('arial', 'Arial'),
        ('times', 'Times New Roman'),
        ('georgia', 'Georgia'),
        ('verdana', 'Verdana')
    ], string='Font Family', default='helvetica')
    
    font_size = fields.Selection([
        ('small', 'Small (10pt)'),
        ('medium', 'Medium (12pt)'),
        ('large', 'Large (14pt)')
    ], string='Font Size', default='medium')
    
    # Layout Style
    layout_style = fields.Selection([
        ('classic', 'Classic'),
        ('modern', 'Modern'),
        ('minimal', 'Minimal'),
        ('professional', 'Professional')
    ], string='Layout Style', default='professional')
    
    # Spacing and Margins
    margin_size = fields.Selection([
        ('narrow', 'Narrow'),
        ('normal', 'Normal'),
        ('wide', 'Wide')
    ], string='Margin Size', default='normal')
    
    line_spacing = fields.Selection([
        ('compact', 'Compact'),
        ('normal', 'Normal'),
        ('relaxed', 'Relaxed')
    ], string='Line Spacing', default='normal')
    
    # ========================
    # CONDITIONAL DISPLAY
    # ========================
    
    # Conditional Fields
    show_if_member_type = fields.Selection([
        ('all', 'All Member Types'),
        ('individual', 'Individual Only'),
        ('corporate', 'Corporate Only'),
        ('student', 'Student Only')
    ], string='Show If Member Type', default='all')
    
    show_if_subscription_status = fields.Selection([
        ('all', 'All Statuses'),
        ('active', 'Active Only'),
        ('renewal', 'Renewal Only'),
        ('new', 'New Members Only')
    ], string='Show If Subscription Status', default='all')
    
    hide_if_zero_amount = fields.Boolean('Hide If Zero Amount', default=True)
    
    # ========================
    # BUSINESS METHODS
    # ========================
    
    def apply_layout_to_invoice(self, invoice):
        """Apply this layout configuration to an invoice"""
        if not invoice:
            return
        
        # Apply layout-specific formatting
        layout_data = self._generate_layout_data(invoice)
        
        # Update invoice with layout data
        invoice.write({
            'layout_data': layout_data,
            'invoice_layout_id': self.id,
        })
        
        return layout_data
    
    def _generate_layout_data(self, invoice):
        """Generate layout data dictionary for invoice"""
        partner = invoice.partner_id
        
        layout_data = {
            'layout_name': self.name,
            'layout_type': self.layout_type,
            'invoice_title': self.invoice_title or self._get_default_title(),
            'reference': self._format_reference(invoice),
            'styling': self._get_styling_data(),
            'sections': self._get_sections_config(),
            'member_info': self._get_member_info_config(partner),
            'payment_info': self._get_payment_info_config(),
            'footer_info': self._get_footer_info_config(),
        }
        
        return layout_data
    
    def _get_default_title(self):
        """Get default title based on layout type"""
        titles = {
            'membership': _('Membership Invoice'),
            'renewal': _('Membership Renewal'),
            'chapter': _('Chapter Fee Invoice'),
            'donation': _('Donation Receipt'),
            'event': _('Event Registration'),
            'publication': _('Publication Invoice'),
            'late_fee': _('Late Fee Notice'),
            'statement': _('Financial Statement'),
        }
        return titles.get(self.layout_type, _('Invoice'))
    
    def _format_reference(self, invoice):
        """Format invoice reference according to template"""
        if not self.reference_format:
            return invoice.name
        
        variables = {
            'year': str(invoice.invoice_date.year),
            'month': f"{invoice.invoice_date.month:02d}",
            'sequence': invoice.name.split('/')[-1] if '/' in invoice.name else invoice.name,
            'member_number': invoice.partner_id.member_number or str(invoice.partner_id.id),
        }
        
        try:
            return self.reference_format.format(**variables)
        except (KeyError, ValueError):
            return invoice.name
    
    def _get_styling_data(self):
        """Get styling configuration"""
        return {
            'primary_color': self.primary_color,
            'secondary_color': self.secondary_color,
            'accent_color': self.accent_color,
            'font_family': self.font_family,
            'font_size': self.font_size,
            'layout_style': self.layout_style,
            'margin_size': self.margin_size,
            'line_spacing': self.line_spacing,
            'currency_position': self.currency_position,
            'number_format': self.number_format,
        }
    
    def _get_sections_config(self):
        """Get sections visibility configuration"""
        return {
            'header': {
                'show_logo': self.show_company_logo,
                'logo_position': self.logo_position,
                'custom_text': self.custom_header_text,
            },
            'member_details': {
                'show_member_number': self.show_member_number,
                'show_member_type': self.show_member_type,
                'show_member_since': self.show_member_since,
                'show_membership_status': self.show_membership_status,
                'show_chapter_affiliation': self.show_chapter_affiliation,
                'show_address': self.show_member_address,
                'show_phone': self.show_member_phone,
                'show_email': self.show_member_email,
            },
            'line_items': {
                'show_product_code': self.show_product_code,
                'show_description': self.show_product_description,
                'show_unit_price': self.show_unit_price,
                'show_quantity': self.show_quantity,
                'show_discount': self.show_discount,
                'show_taxes': self.show_taxes,
                'group_by_subscription_type': self.group_by_subscription_type,
                'group_by_chapter': self.group_by_chapter,
                'sort_by': self.sort_lines_by,
            },
            'totals': {
                'show_subtotal': self.show_subtotal,
                'show_tax_breakdown': self.show_tax_breakdown,
                'show_total_due': self.show_total_due,
                'show_amount_paid': self.show_amount_paid,
                'show_balance_due': self.show_balance_due,
            },
            'footer': {
                'show_company_details': self.show_company_details,
                'show_tax_info': self.show_tax_info,
                'show_bank_details': self.show_bank_details,
                'custom_text': self.custom_footer_text,
                'show_terms': self.show_terms_conditions,
                'show_privacy': self.show_privacy_notice,
            }
        }
    
    def _get_member_info_config(self, partner):
        """Get member-specific information configuration"""
        return {
            'member_number': partner.member_number if self.show_member_number else None,
            'member_type': partner.member_type if self.show_member_type else None,
            'member_since': partner.join_date if self.show_member_since else None,
            'membership_status': partner.member_status if self.show_membership_status else None,
            'chapter': partner.primary_chapter_id.name if self.show_chapter_affiliation and partner.primary_chapter_id else None,
        }
    
    def _get_payment_info_config(self):
        """Get payment information configuration"""
        return {
            'show_payment_terms': self.show_payment_terms,
            'show_due_date': self.show_due_date,
            'show_payment_methods': self.show_payment_methods,
            'payment_instructions': self.payment_instructions,
        }
    
    def _get_footer_info_config(self):
        """Get footer information configuration"""
        return {
            'terms_conditions': self.terms_conditions_text if self.show_terms_conditions else None,
            'privacy_notice': self.privacy_notice_text if self.show_privacy_notice else None,
        }
    
    def action_preview_layout(self):
        """Preview this layout with sample data"""
        # Create a sample invoice context for preview
        return {
            'type': 'ir.actions.act_window',
            'name': f'Preview Layout - {self.name}',
            'res_model': 'multiple.invoice.layout.preview',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_layout_id': self.id,
            }
        }
    
    def action_duplicate_layout(self):
        """Create a copy of this layout"""
        copy_name = f"{self.name} (Copy)"
        copy_vals = self.copy_data()[0]
        copy_vals['name'] = copy_name
        
        new_layout = self.create(copy_vals)
        
        return {
            'type': 'ir.actions.act_window',
            'name': 'Edit Layout Copy',
            'res_model': 'multiple.invoice.layout',
            'view_mode': 'form',
            'res_id': new_layout.id,
            'target': 'current',
        }
    
    @api.model
    def get_default_layout_for_type(self, layout_type):
        """Get default layout for a specific invoice type"""
        layout = self.search([
            ('layout_type', '=', layout_type),
            ('active', '=', True)
        ], limit=1, order='sequence')
        
        return layout
    
    @api.model
    def create_default_layouts(self):
        """Create default layouts for common invoice types"""
        default_layouts = [
            {
                'name': 'Standard Membership Invoice',
                'layout_type': 'membership',
                'invoice_title': 'Membership Invoice',
                'show_subscription_details': True,
                'show_member_number': True,
                'show_chapter_affiliation': True,
            },
            {
                'name': 'Renewal Notice',
                'layout_type': 'renewal',
                'invoice_title': 'Membership Renewal',
                'show_subscription_details': True,
                'show_member_since': True,
                'payment_instructions': '<p>Thank you for your continued membership!</p>',
            },
            {
                'name': 'Chapter Fee Invoice',
                'layout_type': 'chapter',
                'invoice_title': 'Chapter Membership Fee',
                'show_chapter_affiliation': True,
                'group_by_chapter': True,
            },
            {
                'name': 'Donation Receipt',
                'layout_type': 'donation',
                'invoice_title': 'Donation Receipt',
                'show_tax_info': True,
                'show_terms_conditions': True,
                'terms_conditions_text': '<p>Thank you for your generous donation. This receipt serves as acknowledgment of your tax-deductible contribution.</p>',
            },
        ]
        
        created_layouts = []
        for layout_data in default_layouts:
            existing = self.search([
                ('name', '=', layout_data['name']),
                ('layout_type', '=', layout_data['layout_type'])
            ])
            
            if not existing:
                layout = self.create(layout_data)
                created_layouts.append(layout)
        
        return created_layouts
    
    @api.constrains('primary_color', 'secondary_color', 'accent_color')
    def _check_color_format(self):
        """Validate hex color format"""
        import re
        hex_pattern = re.compile(r'^#[0-9A-Fa-f]{6}$')
        
        for layout in self:
            if layout.primary_color and not hex_pattern.match(layout.primary_color):
                raise ValidationError(_('Primary color must be a valid hex color (e.g., #1f2937)'))
            if layout.secondary_color and not hex_pattern.match(layout.secondary_color):
                raise ValidationError(_('Secondary color must be a valid hex color (e.g., #6b7280)'))
            if layout.accent_color and not hex_pattern.match(layout.accent_color):
                raise ValidationError(_('Accent color must be a valid hex color (e.g., #3b82f6)'))


class AccountMove(models.Model):
    """
    Enhanced account move to support layout configuration
    """
    _inherit = 'account.move'
    
    # Layout Configuration
    invoice_layout_id = fields.Many2one('multiple.invoice.layout', 'Invoice Layout')
    layout_data = fields.Text('Layout Data', help="JSON data for invoice layout configuration")
    
    def action_change_layout(self):
        """Change invoice layout"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Change Invoice Layout',
            'res_model': 'multiple.invoice.layout.selector',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_invoice_id': self.id,
                'default_current_layout_id': self.invoice_layout_id.id if self.invoice_layout_id else False,
            }
        }


class MultipleInvoiceLayoutPreview(models.TransientModel):
    """
    Preview wizard for invoice layouts
    """
    _name = 'multiple.invoice.layout.preview'
    _description = 'Invoice Layout Preview'
    
    layout_id = fields.Many2one('multiple.invoice.layout', 'Layout', required=True)
    sample_partner_id = fields.Many2one('res.partner', 'Sample Member',
        domain="[('is_ams_member', '=', True)]")
    
    preview_html = fields.Html('Preview', compute='_compute_preview_html')
    
    @api.depends('layout_id', 'sample_partner_id')
    def _compute_preview_html(self):
        for preview in self:
            if preview.layout_id:
                # Generate sample HTML preview
                preview.preview_html = preview._generate_preview_html()
            else:
                preview.preview_html = '<p>Please select a layout to preview.</p>'
    
    def _generate_preview_html(self):
        """Generate HTML preview of the layout"""
        # This would generate a sample invoice HTML using the layout configuration
        # For now, return a simple preview
        return f"""
        <div style="font-family: {self.layout_id.font_family}; color: {self.layout_id.primary_color};">
            <h2>{self.layout_id.invoice_title or 'Sample Invoice'}</h2>
            <p>This is a preview of the {self.layout_id.name} layout.</p>
            <p>Layout Type: {self.layout_id.layout_type}</p>
            <p>Style: {self.layout_id.layout_style}</p>
        </div>
        """


class MultipleInvoiceLayoutSelector(models.TransientModel):
    """
    Layout selector wizard for changing invoice layouts
    """
    _name = 'multiple.invoice.layout.selector'
    _description = 'Invoice Layout Selector'
    
    invoice_id = fields.Many2one('account.move', 'Invoice', required=True)
    current_layout_id = fields.Many2one('multiple.invoice.layout', 'Current Layout')
    new_layout_id = fields.Many2one('multiple.invoice.layout', 'New Layout', required=True)
    
    def action_apply_layout(self):
        """Apply selected layout to invoice"""
        if self.new_layout_id:
            self.new_layout_id.apply_layout_to_invoice(self.invoice_id)
        
        return {'type': 'ir.actions.act_window_close'}