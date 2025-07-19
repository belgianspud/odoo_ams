from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import logging

_logger = logging.getLogger(__name__)


class MultipleInvoice(models.TransientModel):
    """
    Wizard for creating multiple invoices simultaneously for AMS operations
    """
    _name = 'multiple.invoice'
    _description = 'Multiple Invoice Generation'
    
    # ========================
    # SELECTION CRITERIA
    # ========================
    
    # Invoice Type
    invoice_type = fields.Selection([
        ('membership', 'Membership Billing'),
        ('renewal', 'Renewal Billing'),
        ('chapter', 'Chapter Fees'),
        ('annual_fee', 'Annual Fees'),
        ('custom', 'Custom Billing'),
        ('late_fee', 'Late Fees'),
        ('adjustment', 'Billing Adjustments')
    ], string='Invoice Type', required=True, default='membership')
    
    # Partner Selection
    partner_selection_method = fields.Selection([
        ('all_members', 'All Active Members'),
        ('specific_members', 'Specific Members'),
        ('member_type', 'By Member Type'),
        ('chapter', 'By Chapter'),
        ('subscription_status', 'By Subscription Status'),
        ('custom_filter', 'Custom Filter')
    ], string='Partner Selection', required=True, default='all_members')
    
    # Specific Partner Selection
    partner_ids = fields.Many2many('res.partner', 'multiple_invoice_partner_rel',
                                  'invoice_id', 'partner_id', 'Selected Partners')
    
    # Filter Criteria
    member_type = fields.Selection([
        ('individual', 'Individual Member'),
        ('student', 'Student Member'),
        ('corporate', 'Corporate Member'),
        ('honorary', 'Honorary Member'),
        ('emeritus', 'Emeritus Member'),
        ('associate', 'Associate Member'),
        ('fellow', 'Fellow'),
        ('retired', 'Retired Member')
    ], string='Member Type Filter')
    
    chapter_ids = fields.Many2many('ams.chapter', 'multiple_invoice_chapter_rel',
                                  'invoice_id', 'chapter_id', 'Chapters')
    
    subscription_status = fields.Selection([
        ('active', 'Active Subscriptions'),
        ('expired', 'Expired Subscriptions'),
        ('pending_renewal', 'Pending Renewal'),
        ('no_subscription', 'No Active Subscription')
    ], string='Subscription Status Filter')
    
    # Custom Domain Filter
    custom_domain = fields.Text('Custom Domain Filter',
        help="Python domain filter for advanced partner selection")
    
    # ========================
    # INVOICE CONFIGURATION
    # ========================
    
    # Product/Service
    product_id = fields.Many2one('product.product', 'Product/Service', required=True)
    product_description = fields.Text('Product Description',
        help="Override default product description")
    
    # Pricing
    unit_price = fields.Float('Unit Price', default=0.0)
    use_product_price = fields.Boolean('Use Product Price', default=True)
    apply_member_discount = fields.Boolean('Apply Member Discount', default=False)
    member_discount_percentage = fields.Float('Member Discount %', default=0.0)
    
    # Quantity and Calculations
    quantity = fields.Float('Quantity', default=1.0)
    
    # Taxes
    tax_ids = fields.Many2many('account.tax', 'multiple_invoice_tax_rel',
                              'invoice_id', 'tax_id', 'Taxes')
    
    # ========================
    # INVOICE DETAILS
    # ========================
    
    # Journal and Accounting
    journal_id = fields.Many2one('account.journal', 'Journal', required=True,
        domain="[('type', '=', 'sale')]")
    
    # Dates
    invoice_date = fields.Date('Invoice Date', default=fields.Date.today, required=True)
    due_date = fields.Date('Due Date')
    
    # Payment Terms
    payment_term_id = fields.Many2one('account.payment.term', 'Payment Terms')
    
    # Reference and Communication
    invoice_reference_prefix = fields.Char('Invoice Reference Prefix',
        help="Prefix for invoice references (e.g., 'MEMBERSHIP-2024-')")
    
    communication_message = fields.Text('Communication Message',
        help="Additional message to include in invoices")
    
    # ========================
    # PROCESSING OPTIONS
    # ========================
    
    # Batch Processing
    batch_size = fields.Integer('Batch Size', default=100,
        help="Number of invoices to process at once")
    
    auto_post = fields.Boolean('Auto Post Invoices', default=False,
        help="Automatically post invoices after creation")
    
    auto_send = fields.Boolean('Auto Send Invoices', default=False,
        help="Automatically send invoices via email")
    
    email_template_id = fields.Many2one('mail.template', 'Email Template',
        domain="[('model', '=', 'account.move')]",
        help="Email template for sending invoices")
    
    # Processing Control
    validate_partners = fields.Boolean('Validate Partners', default=True,
        help="Validate partner data before creating invoices")
    
    skip_zero_amount = fields.Boolean('Skip Zero Amount', default=True,
        help="Skip partners with zero amount calculations")
    
    create_separate_lines = fields.Boolean('Create Separate Lines', default=False,
        help="Create separate invoice lines for different subscription types")
    
    # ========================
    # RESULTS AND STATISTICS
    # ========================
    
    # Processing Results
    state = fields.Selection([
        ('draft', 'Draft'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('error', 'Error')
    ], string='Status', default='draft', readonly=True)
    
    partner_count = fields.Integer('Partners Selected', compute='_compute_partner_count')
    invoices_created = fields.Integer('Invoices Created', readonly=True)
    total_amount = fields.Float('Total Amount', readonly=True)
    
    # Error Handling
    error_log = fields.Text('Error Log', readonly=True)
    failed_partners = fields.Text('Failed Partners', readonly=True)
    
    # Generated Invoices
    invoice_ids = fields.One2many('account.move', 'multiple_invoice_id', 'Generated Invoices')
    
    @api.depends('partner_selection_method', 'partner_ids', 'member_type', 'chapter_ids', 'subscription_status')
    def _compute_partner_count(self):
        for wizard in self:
            try:
                partners = wizard._get_selected_partners()
                wizard.partner_count = len(partners)
            except Exception:
                wizard.partner_count = 0
    
    @api.onchange('product_id')
    def _onchange_product_id(self):
        """Update fields when product changes"""
        if self.product_id:
            if self.use_product_price:
                self.unit_price = self.product_id.list_price
            
            self.product_description = self.product_id.description_sale
            
            # Set default taxes
            self.tax_ids = [(6, 0, self.product_id.taxes_id.ids)]
    
    @api.onchange('use_product_price', 'product_id')
    def _onchange_use_product_price(self):
        """Update price when switching to product price"""
        if self.use_product_price and self.product_id:
            self.unit_price = self.product_id.list_price
    
    @api.onchange('invoice_date', 'payment_term_id')
    def _onchange_invoice_date(self):
        """Calculate due date based on payment terms"""
        if self.invoice_date and self.payment_term_id:
            # Calculate due date based on payment terms
            term_lines = self.payment_term_id.line_ids.sorted('days')
            if term_lines:
                max_days = max(term_lines.mapped('days'))
                self.due_date = self.invoice_date + timedelta(days=max_days)
    
    @api.onchange('partner_selection_method')
    def _onchange_partner_selection_method(self):
        """Clear selection when method changes"""
        self.partner_ids = [(5, 0, 0)]  # Clear all partners
        
        # Set defaults based on selection method
        if self.partner_selection_method == 'all_members':
            pass  # No additional setup needed
        elif self.partner_selection_method == 'chapter':
            self.chapter_ids = [(5, 0, 0)]  # Clear chapters
        elif self.partner_selection_method == 'member_type':
            self.member_type = False
        elif self.partner_selection_method == 'subscription_status':
            self.subscription_status = False
    
    def _get_selected_partners(self):
        """Get partners based on selection criteria"""
        domain = [('is_ams_member', '=', True)]
        
        if self.partner_selection_method == 'all_members':
            domain.append(('member_status', '=', 'active'))
        
        elif self.partner_selection_method == 'specific_members':
            if not self.partner_ids:
                return self.env['res.partner']
            return self.partner_ids
        
        elif self.partner_selection_method == 'member_type':
            if self.member_type:
                domain.append(('member_type', '=', self.member_type))
        
        elif self.partner_selection_method == 'chapter':
            if self.chapter_ids:
                # Get partners with subscriptions in selected chapters
                chapter_subscriptions = self.env['ams.subscription'].search([
                    ('chapter_id', 'in', self.chapter_ids.ids),
                    ('state', '=', 'active')
                ])
                partner_ids = chapter_subscriptions.mapped('partner_id').ids
                domain.append(('id', 'in', partner_ids))
        
        elif self.partner_selection_method == 'subscription_status':
            if self.subscription_status == 'active':
                domain.append(('active_subscription_count', '>', 0))
            elif self.subscription_status == 'expired':
                domain.append(('expired_subscription_count', '>', 0))
                domain.append(('active_subscription_count', '=', 0))
            elif self.subscription_status == 'pending_renewal':
                domain.append(('pending_renewal_count', '>', 0))
            elif self.subscription_status == 'no_subscription':
                domain.append(('total_subscription_count', '=', 0))
        
        elif self.partner_selection_method == 'custom_filter' and self.custom_domain:
            try:
                # Parse custom domain
                import ast
                custom_filter = ast.literal_eval(self.custom_domain)
                domain.extend(custom_filter)
            except Exception as e:
                raise UserError(_('Invalid custom domain filter: %s') % str(e))
        
        return self.env['res.partner'].search(domain)
    
    def action_preview_partners(self):
        """Preview selected partners before invoice creation"""
        partners = self._get_selected_partners()
        
        return {
            'type': 'ir.actions.act_window',
            'name': 'Selected Partners Preview',
            'res_model': 'res.partner',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', partners.ids)],
            'context': {
                'search_default_group_by_member_type': 1,
                'create': False,
                'edit': False,
            }
        }
    
    def action_generate_invoices(self):
        """Generate invoices for selected partners"""
        try:
            self.state = 'processing'
            
            # Validate configuration
            self._validate_configuration()
            
            # Get selected partners
            partners = self._get_selected_partners()
            
            if not partners:
                raise UserError(_('No partners selected for invoice generation.'))
            
            # Process in batches
            created_invoices = self._process_partners_in_batches(partners)
            
            # Update statistics
            self.invoices_created = len(created_invoices)
            self.total_amount = sum(created_invoices.mapped('amount_total'))
            self.state = 'completed'
            
            # Return action to view created invoices
            return self._get_invoices_action(created_invoices)
            
        except Exception as e:
            self.state = 'error'
            self.error_log = str(e)
            _logger.error(f"Multiple invoice generation failed: {str(e)}")
            raise UserError(_('Invoice generation failed: %s') % str(e))
    
    def _validate_configuration(self):
        """Validate wizard configuration"""
        if not self.product_id:
            raise UserError(_('Product/Service is required.'))
        
        if self.unit_price < 0:
            raise UserError(_('Unit price cannot be negative.'))
        
        if self.quantity <= 0:
            raise UserError(_('Quantity must be greater than zero.'))
        
        if not self.journal_id:
            raise UserError(_('Journal is required.'))
        
        if self.auto_send and not self.email_template_id:
            raise UserError(_('Email template is required for auto-sending invoices.'))
    
    def _process_partners_in_batches(self, partners):
        """Process partners in batches to avoid memory issues"""
        created_invoices = self.env['account.move']
        failed_partners = []
        
        # Process in batches
        for i in range(0, len(partners), self.batch_size):
            batch_partners = partners[i:i + self.batch_size]
            
            for partner in batch_partners:
                try:
                    invoice = self._create_invoice_for_partner(partner)
                    if invoice:
                        created_invoices |= invoice
                except Exception as e:
                    failed_partners.append(f"{partner.name}: {str(e)}")
                    _logger.error(f"Failed to create invoice for {partner.name}: {str(e)}")
        
        # Log failed partners
        if failed_partners:
            self.failed_partners = '\n'.join(failed_partners)
        
        return created_invoices
    
    def _create_invoice_for_partner(self, partner):
        """Create invoice for a specific partner"""
        # Calculate effective price
        effective_price = self._calculate_effective_price(partner)
        
        # Skip if zero amount and configured to skip
        if self.skip_zero_amount and effective_price <= 0:
            return False
        
        # Validate partner if required
        if self.validate_partners:
            self._validate_partner(partner)
        
        # Prepare invoice values
        invoice_vals = self._prepare_invoice_values(partner, effective_price)
        
        # Create invoice
        invoice = self.env['account.move'].create(invoice_vals)
        
        # Post invoice if auto-post enabled
        if self.auto_post:
            invoice.action_post()
        
        # Send invoice if auto-send enabled
        if self.auto_send and self.email_template_id:
            self.email_template_id.send_mail(invoice.id, force_send=False)
        
        return invoice
    
    def _calculate_effective_price(self, partner):
        """Calculate effective price for partner"""
        price = self.unit_price
        
        # Apply member discount if configured
        if self.apply_member_discount and self.member_discount_percentage > 0:
            if partner.member_status == 'active':
                discount = price * (self.member_discount_percentage / 100)
                price = price - discount
        
        # Use product-specific pricing logic if available
        if hasattr(self.product_id, 'get_effective_price'):
            price = self.product_id.get_effective_price(
                partner=partner,
                quantity=self.quantity,
                date=self.invoice_date
            )
        
        return max(0, price)  # Ensure non-negative price
    
    def _validate_partner(self, partner):
        """Validate partner before creating invoice"""
        # Check if partner has required information
        if not partner.email and self.auto_send:
            raise UserError(_('Partner %s has no email address but auto-send is enabled.') % partner.name)
        
        # Check credit limit if enabled
        if hasattr(partner, 'check_credit_limit'):
            amount = self._calculate_effective_price(partner) * self.quantity
            can_invoice, message = partner.check_credit_limit(amount)
            if not can_invoice:
                raise UserError(_('Credit check failed for %s: %s') % (partner.name, message))
    
    def _prepare_invoice_values(self, partner, effective_price):
        """Prepare invoice values for partner"""
        # Generate invoice reference
        invoice_ref = self._generate_invoice_reference(partner)
        
        # Prepare invoice line
        line_vals = {
            'product_id': self.product_id.id,
            'name': self.product_description or self.product_id.name,
            'quantity': self.quantity,
            'price_unit': effective_price,
            'tax_ids': [(6, 0, self.tax_ids.ids)],
        }
        
        # Add analytic account if product is AMS-related
        if hasattr(self.product_id, 'is_ams_product') and self.product_id.is_ams_product:
            if partner.primary_chapter_id and partner.primary_chapter_id.analytic_account_id:
                line_vals['analytic_account_id'] = partner.primary_chapter_id.analytic_account_id.id
        
        invoice_vals = {
            'partner_id': partner.id,
            'move_type': 'out_invoice',
            'journal_id': self.journal_id.id,
            'invoice_date': self.invoice_date,
            'invoice_date_due': self.due_date,
            'payment_term_id': self.payment_term_id.id if self.payment_term_id else False,
            'ref': invoice_ref,
            'narration': self.communication_message,
            'multiple_invoice_id': self.id,
            'invoice_line_ids': [(0, 0, line_vals)],
        }
        
        # Add AMS-specific fields
        if self.invoice_type == 'membership':
            invoice_vals['is_ams_subscription_invoice'] = True
        elif self.invoice_type == 'renewal':
            invoice_vals['is_ams_renewal_invoice'] = True
        elif self.invoice_type == 'chapter':
            invoice_vals['is_ams_chapter_fee'] = True
            if partner.primary_chapter_id:
                invoice_vals['ams_chapter_id'] = partner.primary_chapter_id.id
        
        return invoice_vals
    
    def _generate_invoice_reference(self, partner):
        """Generate invoice reference for partner"""
        reference = self.invoice_reference_prefix or ''
        
        # Add member number if available
        if partner.member_number:
            reference += partner.member_number
        else:
            reference += str(partner.id)
        
        # Add date
        reference += f"-{self.invoice_date.strftime('%Y%m%d')}"
        
        return reference
    
    def _get_invoices_action(self, invoices):
        """Return action to view created invoices"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Generated Invoices',
            'res_model': 'account.move',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', invoices.ids)],
            'context': {
                'search_default_group_by_partner': 1,
                'search_default_state_posted': 1 if self.auto_post else 0,
            }
        }
    
    def action_view_generated_invoices(self):
        """View all generated invoices"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Generated Invoices',
            'res_model': 'account.move',
            'view_mode': 'tree,form',
            'domain': [('multiple_invoice_id', '=', self.id)],
            'context': {'create': False}
        }
    
    @api.constrains('batch_size')
    def _check_batch_size(self):
        if self.batch_size <= 0:
            raise ValidationError(_('Batch size must be greater than zero.'))
    
    @api.constrains('member_discount_percentage')
    def _check_member_discount(self):
        if self.member_discount_percentage < 0 or self.member_discount_percentage > 100:
            raise ValidationError(_('Member discount percentage must be between 0 and 100.'))


class AccountMove(models.Model):
    """
    Enhanced account move to track multiple invoice generation
    """
    _inherit = 'account.move'
    
    multiple_invoice_id = fields.Many2one('multiple.invoice', 'Multiple Invoice Batch',
        help="Batch that generated this invoice")
    
    def action_view_batch_details(self):
        """View details of the batch that created this invoice"""
        if self.multiple_invoice_id:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Batch Details',
                'res_model': 'multiple.invoice',
                'view_mode': 'form',
                'res_id': self.multiple_invoice_id.id,
                'target': 'new',
            }


class MultipleInvoiceTemplate(models.Model):
    """
    Templates for common multiple invoice scenarios
    """
    _name = 'multiple.invoice.template'
    _description = 'Multiple Invoice Template'
    _order = 'name'
    
    name = fields.Char('Template Name', required=True)
    description = fields.Text('Description')
    
    # Template Configuration
    invoice_type = fields.Selection([
        ('membership', 'Membership Billing'),
        ('renewal', 'Renewal Billing'),
        ('chapter', 'Chapter Fees'),
        ('annual_fee', 'Annual Fees'),
        ('custom', 'Custom Billing'),
        ('late_fee', 'Late Fees'),
        ('adjustment', 'Billing Adjustments')
    ], string='Invoice Type', required=True)
    
    partner_selection_method = fields.Selection([
        ('all_members', 'All Active Members'),
        ('specific_members', 'Specific Members'),
        ('member_type', 'By Member Type'),
        ('chapter', 'By Chapter'),
        ('subscription_status', 'By Subscription Status'),
        ('custom_filter', 'Custom Filter')
    ], string='Partner Selection', required=True)
    
    product_id = fields.Many2one('product.product', 'Default Product/Service')
    journal_id = fields.Many2one('account.journal', 'Default Journal',
        domain="[('type', '=', 'sale')]")
    payment_term_id = fields.Many2one('account.payment.term', 'Default Payment Terms')
    
    # Template Settings
    auto_post = fields.Boolean('Auto Post Invoices', default=False)
    auto_send = fields.Boolean('Auto Send Invoices', default=False)
    email_template_id = fields.Many2one('mail.template', 'Email Template',
        domain="[('model', '=', 'account.move')]")
    
    def action_use_template(self):
        """Create multiple invoice wizard with template values"""
        wizard_vals = {
            'invoice_type': self.invoice_type,
            'partner_selection_method': self.partner_selection_method,
            'product_id': self.product_id.id if self.product_id else False,
            'journal_id': self.journal_id.id if self.journal_id else False,
            'payment_term_id': self.payment_term_id.id if self.payment_term_id else False,
            'auto_post': self.auto_post,
            'auto_send': self.auto_send,
            'email_template_id': self.email_template_id.id if self.email_template_id else False,
        }
        
        wizard = self.env['multiple.invoice'].create(wizard_vals)
        
        return {
            'type': 'ir.actions.act_window',
            'name': f'Multiple Invoice - {self.name}',
            'res_model': 'multiple.invoice',
            'view_mode': 'form',
            'res_id': wizard.id,
            'target': 'new',
        }