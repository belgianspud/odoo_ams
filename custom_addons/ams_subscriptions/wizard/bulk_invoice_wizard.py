from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from dateutil.relativedelta import relativedelta
import logging

_logger = logging.getLogger(__name__)


class BulkInvoiceWizard(models.TransientModel):
    _name = 'ams.bulk.invoice.wizard'
    _description = 'Bulk Invoice Generation Wizard'

    # Invoice Type
    invoice_type = fields.Selection([
        ('membership_renewal', 'Membership Renewals'),
        ('membership_dues', 'Membership Dues'),
        ('late_fees', 'Late Fees'),
        ('adjustment', 'Billing Adjustments'),
        ('custom', 'Custom Invoices')
    ], string='Invoice Type', required=True, default='membership_renewal')

    # Selection Criteria
    selection_method = fields.Selection([
        ('criteria', 'By Criteria'),
        ('manual', 'Manual Selection'),
        ('scheduled', 'Scheduled Renewals')
    ], string='Selection Method', default='criteria', required=True)

    # Manual Selection
    subscription_ids = fields.Many2many(
        'ams.member.subscription',
        string='Subscriptions to Invoice'
    )
    
    partner_ids = fields.Many2many(
        'res.partner',
        string='Members to Invoice',
        domain=[('is_member', '=', True)]
    )

    # Criteria Selection
    membership_type_ids = fields.Many2many(
        'ams.membership.type',
        'bulk_invoice_membership_type_rel',
        string='Membership Types'
    )
    
    chapter_ids = fields.Many2many(
        'ams.chapter',
        'bulk_invoice_chapter_rel',
        string='Chapters'
    )
    
    subscription_states = fields.Selection([
        ('all', 'All States'),
        ('active', 'Active'),
        ('pending_renewal', 'Pending Renewal'),
        ('expired', 'Expired'),
        ('lapsed', 'Lapsed')
    ], string='Subscription States', default='active')

    # Date Filters
    renewal_date_from = fields.Date(
        string='Renewal Date From',
        help="Include subscriptions with renewal date from this date"
    )
    
    renewal_date_to = fields.Date(
        string='Renewal Date To',
        help="Include subscriptions with renewal date up to this date"
    )
    
    expiry_date_from = fields.Date(
        string='Expiry Date From',
        help="Include subscriptions expiring from this date"
    )
    
    expiry_date_to = fields.Date(
        string='Expiry Date To',
        help="Include subscriptions expiring up to this date"
    )

    # Invoice Settings
    invoice_date = fields.Date(
        string='Invoice Date',
        default=fields.Date.context_today,
        required=True
    )
    
    due_date = fields.Date(
        string='Due Date',
        help="Payment due date (if not set, uses payment terms)"
    )
    
    payment_term_id = fields.Many2one(
        'account.payment.term',
        string='Payment Terms',
        help="Payment terms for the invoices"
    )

    # Invoice Content
    invoice_description = fields.Text(
        string='Invoice Description',
        default="Membership Services",
        help="Description to appear on invoice lines"
    )
    
    custom_message = fields.Html(
        string='Custom Message',
        help="Custom message to include on invoices"
    )
    
    include_membership_details = fields.Boolean(
        string='Include Membership Details',
        default=True,
        help="Include membership type and period details"
    )

    # Pricing Options
    pricing_option = fields.Selection([
        ('standard', 'Standard Pricing'),
        ('custom', 'Custom Amount'),
        ('late_fee', 'Late Fee Calculation'),
        ('prorate', 'Prorated Amount')
    ], string='Pricing Option', default='standard', required=True)
    
    custom_amount = fields.Float(
        string='Custom Amount',
        digits='Product Price',
        help="Fixed amount for all invoices"
    )
    
    late_fee_percentage = fields.Float(
        string='Late Fee Percentage',
        digits='Discount',
        default=5.0,
        help="Late fee as percentage of original amount"
    )
    
    late_fee_minimum = fields.Float(
        string='Minimum Late Fee',
        digits='Product Price',
        default=10.0,
        help="Minimum late fee amount"
    )
    
    prorate_from_date = fields.Date(
        string='Prorate From Date',
        help="Start date for proration calculation"
    )
    
    prorate_to_date = fields.Date(
        string='Prorate To Date',
        help="End date for proration calculation"
    )

    # Discounts and Adjustments
    apply_discount = fields.Boolean(
        string='Apply Discount',
        default=False
    )
    
    discount_type = fields.Selection([
        ('percentage', 'Percentage'),
        ('fixed', 'Fixed Amount')
    ], string='Discount Type', default='percentage')
    
    discount_percentage = fields.Float(
        string='Discount Percentage',
        digits='Discount'
    )
    
    discount_amount = fields.Float(
        string='Discount Amount',
        digits='Product Price'
    )
    
    discount_reason = fields.Char(
        string='Discount Reason',
        help="Reason for applying discount"
    )

    # Processing Options
    auto_post_invoices = fields.Boolean(
        string='Auto-Post Invoices',
        default=False,
        help="Automatically post invoices after creation"
    )
    
    send_by_email = fields.Boolean(
        string='Send by Email',
        default=True,
        help="Send invoices by email to customers"
    )
    
    email_template_id = fields.Many2one(
        'mail.template',
        string='Email Template',
        domain=[('model', '=', 'account.move')],
        help="Email template for sending invoices"
    )
    
    batch_size = fields.Integer(
        string='Batch Size',
        default=50,
        help="Number of invoices to process at once"
    )
    
    grouping_option = fields.Selection([
        ('per_subscription', 'One Invoice per Subscription'),
        ('per_member', 'One Invoice per Member'),
        ('per_chapter', 'One Invoice per Chapter')
    ], string='Invoice Grouping', default='per_subscription', required=True)

    # Preview and Validation
    target_count = fields.Integer(
        string='Records to Invoice',
        compute='_compute_target_count'
    )
    
    estimated_total = fields.Float(
        string='Estimated Total Amount',
        compute='_compute_estimated_total',
        digits='Product Price'
    )
    
    preview_data = fields.Html(
        string='Invoice Preview',
        compute='_compute_preview_data'
    )
    
    validation_messages = fields.Html(
        string='Validation Messages',
        compute='_compute_validation_messages'
    )

    # Processing Results
    processing_log = fields.Html(
        string='Processing Log',
        readonly=True
    )
    
    invoices_created = fields.Integer(
        string='Invoices Created',
        readonly=True
    )
    
    total_amount_invoiced = fields.Float(
        string='Total Amount Invoiced',
        digits='Product Price',
        readonly=True
    )
    
    success_count = fields.Integer(
        string='Successful',
        readonly=True
    )
    
    error_count = fields.Integer(
        string='Errors',
        readonly=True
    )

    def _get_record_ids(self, recordset):
        """Helper method to safely get IDs from a recordset"""
        if not recordset:
            return []
        
        try:
            return recordset.ids
        except AttributeError:
            try:
                return recordset.mapped('id')
            except AttributeError:
                return []

    @api.depends('selection_method', 'subscription_ids', 'partner_ids', 'membership_type_ids',
                 'chapter_ids', 'subscription_states', 'renewal_date_from', 'renewal_date_to',
                 'expiry_date_from', 'expiry_date_to')
    def _compute_target_count(self):
        """Compute number of records to invoice"""
        for wizard in self:
            targets = wizard._get_target_records()
            wizard.target_count = len(targets)

    @api.depends('target_count', 'pricing_option', 'custom_amount')
    def _compute_estimated_total(self):
        """Compute estimated total amount"""
        for wizard in self:
            if wizard.target_count == 0:
                wizard.estimated_total = 0.0
                continue
            
            targets = wizard._get_target_records()
            total = 0.0
            
            for target in targets:
                amount = wizard._calculate_invoice_amount(target)
                total += amount
            
            wizard.estimated_total = total

    @api.depends('target_count')
    def _compute_preview_data(self):
        """Compute preview data"""
        for wizard in self:
            if wizard.target_count == 0:
                wizard.preview_data = "<p>No records found matching the criteria.</p>"
                continue
            
            targets = wizard._get_target_records()
            preview_html = "<table class='table table-sm'>"
            preview_html += "<thead><tr><th>Member</th><th>Type</th><th>Chapter</th><th>Amount</th><th>Due Date</th></tr></thead>"
            preview_html += "<tbody>"
            
            for target in targets[:10]:  # Show max 10 for preview
                try:
                    amount = wizard._calculate_invoice_amount(target)
                    member_name = wizard._get_member_name(target)
                    membership_type = wizard._get_membership_type(target)
                    chapter_name = wizard._get_chapter_name(target)
                    due_date = wizard.due_date or wizard.invoice_date
                    
                    preview_html += f"""
                    <tr>
                        <td>{member_name}</td>
                        <td>{membership_type}</td>
                        <td>{chapter_name}</td>
                        <td>${amount:.2f}</td>
                        <td>{due_date}</td>
                    </tr>
                    """
                except Exception as e:
                    _logger.error(f"Error in preview generation: {e}")
                    continue
            
            if len(targets) > 10:
                preview_html += f"<tr><td colspan='5'><em>... and {len(targets) - 10} more</em></td></tr>"
            
            preview_html += f"<tr class='table-info'><td colspan='4'><strong>Total Estimated</strong></td><td><strong>${wizard.estimated_total:.2f}</strong></td></tr>"
            preview_html += "</tbody></table>"
            
            wizard.preview_data = preview_html

    @api.depends('invoice_type', 'selection_method', 'invoice_date', 'pricing_option')
    def _compute_validation_messages(self):
        """Compute validation messages"""
        for wizard in self:
            messages = []
            
            # Check invoice date
            if not wizard.invoice_date:
                messages.append("Invoice date is required")
            elif wizard.invoice_date > fields.Date.today() + relativedelta(days=30):
                messages.append("Invoice date is too far in the future")
            
            # Check selection
            if wizard.selection_method == 'manual':
                if not wizard.subscription_ids and not wizard.partner_ids:
                    messages.append("Please select subscriptions or members to invoice")
            elif wizard.selection_method == 'criteria':
                if wizard.target_count == 0:
                    messages.append("No records match the selected criteria")
            
            # Check pricing
            if wizard.pricing_option == 'custom' and wizard.custom_amount <= 0:
                messages.append("Custom amount must be greater than zero")
            elif wizard.pricing_option == 'prorate':
                if not wizard.prorate_from_date or not wizard.prorate_to_date:
                    messages.append("Proration dates are required for prorated invoicing")
                elif wizard.prorate_from_date >= wizard.prorate_to_date:
                    messages.append("Prorate from date must be before to date")
            
            # Check email settings
            if wizard.send_by_email and not wizard.email_template_id:
                messages.append("Email template is required when sending by email")
            
            if messages:
                wizard.validation_messages = "<div class='alert alert-warning'><ul><li>" + "</li><li>".join(messages) + "</li></ul></div>"
            else:
                wizard.validation_messages = "<div class='alert alert-success'>✓ Ready to process</div>"

    @api.onchange('invoice_type')
    def _onchange_invoice_type(self):
        """Update fields based on invoice type"""
        if self.invoice_type == 'membership_renewal':
            self.invoice_description = "Membership Renewal"
            self.pricing_option = 'standard'
        elif self.invoice_type == 'membership_dues':
            self.invoice_description = "Membership Dues"
            self.pricing_option = 'standard'
        elif self.invoice_type == 'late_fees':
            self.invoice_description = "Late Fee"
            self.pricing_option = 'late_fee'
        elif self.invoice_type == 'adjustment':
            self.invoice_description = "Billing Adjustment"
            self.pricing_option = 'custom'

    @api.onchange('selection_method')
    def _onchange_selection_method(self):
        """Clear fields when selection method changes"""
        if self.selection_method == 'criteria':
            self.subscription_ids = [(5, 0, 0)]
            self.partner_ids = [(5, 0, 0)]
        elif self.selection_method == 'manual':
            self.membership_type_ids = [(5, 0, 0)]
            self.chapter_ids = [(5, 0, 0)]

    @api.onchange('pricing_option')
    def _onchange_pricing_option(self):
        """Clear fields when pricing option changes"""
        if self.pricing_option != 'custom':
            self.custom_amount = 0.0
        if self.pricing_option != 'late_fee':
            self.late_fee_percentage = 5.0
            self.late_fee_minimum = 10.0
        if self.pricing_option != 'prorate':
            self.prorate_from_date = False
            self.prorate_to_date = False

    def _get_target_records(self):
        """Get target records for invoicing"""
        self.ensure_one()
        
        if self.selection_method == 'manual':
            if self.subscription_ids:
                return self.subscription_ids
            elif self.partner_ids:
                # Get active subscriptions for selected partners
                return self.env['ams.member.subscription'].search([
                    ('partner_id', 'in', self.partner_ids.ids),
                    ('state', 'in', ['active', 'pending_renewal'])
                ])
        
        elif self.selection_method == 'criteria':
            domain = []
            
            # Filter by subscription states
            if self.subscription_states != 'all':
                domain.append(('state', '=', self.subscription_states))
            else:
                domain.append(('state', 'in', ['active', 'pending_renewal', 'expired', 'lapsed']))
            
            # Filter by membership types
            membership_type_ids = self._get_record_ids(self.membership_type_ids)
            if membership_type_ids:
                domain.append(('membership_type_id', 'in', membership_type_ids))
            
            # Filter by chapters
            chapter_ids = self._get_record_ids(self.chapter_ids)
            if chapter_ids:
                domain.append(('chapter_id', 'in', chapter_ids))
            
            # Filter by renewal dates
            if self.renewal_date_from:
                domain.append(('renewal_date', '>=', self.renewal_date_from))
            if self.renewal_date_to:
                domain.append(('renewal_date', '<=', self.renewal_date_to))
            
            # Filter by expiry dates
            if self.expiry_date_from:
                domain.append(('end_date', '>=', self.expiry_date_from))
            if self.expiry_date_to:
                domain.append(('end_date', '<=', self.expiry_date_to))
            
            return self.env['ams.member.subscription'].search(domain)
        
        elif self.selection_method == 'scheduled':
            # Find subscriptions that need renewal invoices
            today = fields.Date.today()
            return self.env['ams.member.subscription'].search([
                ('state', '=', 'active'),
                ('renewal_date', '<=', today),
                ('renewal_sent', '=', False)
            ])
        
        return self.env['ams.member.subscription'].browse([])

    def _calculate_invoice_amount(self, target):
        """Calculate invoice amount for a target record"""
        self.ensure_one()
        
        if self.pricing_option == 'custom':
            base_amount = self.custom_amount
        elif self.pricing_option == 'late_fee':
            original_amount = target.total_amount or target.unit_price
            late_fee = max(
                original_amount * (self.late_fee_percentage / 100),
                self.late_fee_minimum
            )
            base_amount = late_fee
        elif self.pricing_option == 'prorate':
            base_amount = self._calculate_prorated_amount(target)
        else:  # standard
            base_amount = target.membership_type_id.price if target.membership_type_id else 0.0
        
        # Apply discount if configured
        if self.apply_discount:
            if self.discount_type == 'percentage':
                discount = base_amount * (self.discount_percentage / 100)
                base_amount -= discount
            else:  # fixed
                base_amount -= self.discount_amount
        
        return max(0.0, base_amount)

    def _calculate_prorated_amount(self, subscription):
        """Calculate prorated amount for a subscription"""
        if not self.prorate_from_date or not self.prorate_to_date:
            return 0.0
        
        total_days = (self.prorate_to_date - self.prorate_from_date).days
        if total_days <= 0:
            return 0.0
        
        # Calculate based on annual membership price
        annual_price = subscription.membership_type_id.price if subscription.membership_type_id else 0.0
        daily_rate = annual_price / 365
        
        return daily_rate * total_days

    def _get_member_name(self, target):
        """Get member name from target record"""
        try:
            if hasattr(target, 'partner_id') and target.partner_id:
                return target.partner_id.name
            elif hasattr(target, 'name'):
                return target.name
        except AttributeError:
            pass
        return 'Unknown'

    def _get_membership_type(self, target):
        """Get membership type from target record"""
        try:
            if hasattr(target, 'membership_type_id') and target.membership_type_id:
                return target.membership_type_id.name
        except AttributeError:
            pass
        return 'Unknown'

    def _get_chapter_name(self, target):
        """Get chapter name from target record"""
        try:
            if hasattr(target, 'chapter_id') and target.chapter_id:
                return target.chapter_id.name
        except AttributeError:
            pass
        return 'None'

    def action_preview_invoices(self):
        """Preview the invoices to be created"""
        self.ensure_one()
        
        # Force recompute
        self._compute_target_count()
        self._compute_estimated_total()
        self._compute_preview_data()
        self._compute_validation_messages()
        
        if "alert-warning" in (self.validation_messages or ""):
            raise UserError(_("Please fix validation issues before previewing"))
        
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'ams.bulk.invoice.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
            'context': {'show_preview': True}
        }

    def action_create_invoices(self):
        """Create the bulk invoices"""
        self.ensure_one()
        
        # Validate
        self._compute_validation_messages()
        if "alert-warning" in (self.validation_messages or ""):
            raise UserError(_("Please fix validation issues before proceeding"))
        
        targets = self._get_target_records()
        if not targets:
            raise UserError(_("No records found to invoice"))
        
        # Process in batches
        processing_log = []
        invoices_created = 0
        total_amount = 0.0
        success_count = 0
        error_count = 0
        
        # Split into batches
        batch_size = self.batch_size
        batches = [targets[i:i + batch_size] for i in range(0, len(targets), batch_size)]
        
        for batch_num, batch in enumerate(batches, 1):
            processing_log.append(f"<h5>Processing Batch {batch_num}/{len(batches)}</h5>")
            
            batch_results = self._process_batch(batch)
            
            invoices_created += batch_results['invoices_created']
            total_amount += batch_results['total_amount']
            success_count += batch_results['success_count']
            error_count += batch_results['error_count']
            processing_log.extend(batch_results['log'])
            
            # Commit after each batch
            self.env.cr.commit()
        
        # Update wizard with results
        self.processing_log = '<br/>'.join(processing_log)
        self.invoices_created = invoices_created
        self.total_amount_invoiced = total_amount
        self.success_count = success_count
        self.error_count = error_count
        
        message = _("Created %s invoices totaling $%s (%s successful, %s errors)") % (
            invoices_created, total_amount, success_count, error_count
        )
        
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'ams.bulk.invoice.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'show_results': True,
                'result_message': message
            }
        }

    def _process_batch(self, batch):
        """Process a batch of records"""
        self.ensure_one()
        
        results = {
            'invoices_created': 0,
            'total_amount': 0.0,
            'success_count': 0,
            'error_count': 0,
            'log': []
        }
        
        # Group records if needed
        if self.grouping_option == 'per_member':
            grouped_records = self._group_by_member(batch)
        elif self.grouping_option == 'per_chapter':
            grouped_records = self._group_by_chapter(batch)
        else:  # per_subscription
            grouped_records = {record.id: [record] for record in batch}
        
        for group_key, records in grouped_records.items():
            try:
                invoice = self._create_group_invoice(records)
                
                if invoice:
                    results['invoices_created'] += 1
                    results['total_amount'] += invoice.amount_total
                    results['success_count'] += len(records)
                    
                    # Post invoice if requested
                    if self.auto_post_invoices:
                        invoice.action_post()
                    
                    # Send by email if requested
                    if self.send_by_email and self.email_template_id:
                        self._send_invoice_email(invoice)
                    
                    member_names = ', '.join([self._get_member_name(r) for r in records])
                    results['log'].append(f"✓ Created invoice for {member_names} - ${invoice.amount_total:.2f}")
                
            except Exception as e:
                results['error_count'] += len(records)
                member_names = ', '.join([self._get_member_name(r) for r in records])
                error_msg = f"✗ Failed for {member_names}: {str(e)}"
                results['log'].append(error_msg)
                _logger.error(f"Bulk invoice creation failed: {e}")
        
        return results

    def _group_by_member(self, records):
        """Group records by member"""
        grouped = {}
        for record in records:
            partner_id = record.partner_id.id if record.partner_id else 0
            if partner_id not in grouped:
                grouped[partner_id] = []
            grouped[partner_id].append(record)
        return grouped

    def _group_by_chapter(self, records):
        """Group records by chapter"""
        grouped = {}
        for record in records:
            chapter_id = record.chapter_id.id if record.chapter_id else 0
            if chapter_id not in grouped:
                grouped[chapter_id] = []
            grouped[chapter_id].append(record)
        return grouped

    def _create_group_invoice(self, records):
        """Create invoice for a group of records"""
        self.ensure_one()
        
        if not records:
            return None
        
        # Use first record for partner info
        first_record = records[0]
        partner = first_record.partner_id if hasattr(first_record, 'partner_id') else None
        
        if not partner:
            raise UserError(_("No partner found for invoice creation"))
        
        # Prepare invoice lines
        invoice_lines = []
        for record in records:
            amount = self._calculate_invoice_amount(record)
            if amount > 0:
                line_vals = {
                    'name': self._build_invoice_line_description(record),
                    'quantity': 1,
                    'price_unit': amount,
                    'account_id': self._get_income_account().id,
                }
                
                # Add discount if applicable
                if self.apply_discount and self.discount_type == 'percentage':
                    line_vals['discount'] = self.discount_percentage
                
                invoice_lines.append((0, 0, line_vals))
        
        if not invoice_lines:
            return None
        
        # Create invoice
        invoice_vals = {
            'partner_id': partner.id,
            'move_type': 'out_invoice',
            'invoice_date': self.invoice_date,
            'invoice_line_ids': invoice_lines,
        }
        
        # Set due date or payment terms
        if self.due_date:
            invoice_vals['invoice_date_due'] = self.due_date
        elif self.payment_term_id:
            invoice_vals['invoice_payment_term_id'] = self.payment_term_id.id
        
        # Add custom message if provided
        if self.custom_message:
            invoice_vals['narration'] = self.custom_message
        
        invoice = self.env['account.move'].create(invoice_vals)
        
        # Link to subscriptions
        for record in records:
            if hasattr(record, 'invoice_ids'):
                record.invoice_ids = [(4, invoice.id)]
        
        return invoice

    def _build_invoice_line_description(self, record):
        """Build description for invoice line"""
        description = self.invoice_description or "Membership Services"
        
        if self.include_membership_details and hasattr(record, 'membership_type_id'):
            if record.membership_type_id:
                description += f" - {record.membership_type_id.name}"
            
            if hasattr(record, 'start_date') and hasattr(record, 'end_date'):
                if record.start_date and record.end_date:
                    description += f" ({record.start_date} to {record.end_date})"
        
        return description

    def _get_income_account(self):
        """Get appropriate income account"""
        # Default implementation - can be customized
        account = self.env['account.account'].search([
            ('code', 'like', '4%'),
            ('company_id', '=', self.env.company.id)
        ], limit=1)
        
        if not account:
            raise UserError(_("No income account found. Please configure your chart of accounts."))
        
        return account

    def _send_invoice_email(self, invoice):
        """Send invoice by email"""
        try:
            email_values = {}
            if self.custom_message:
                email_values['body_html'] = self.custom_message
            
            self.email_template_id.send_mail(
                invoice.id,
                force_send=True,
                email_values=email_values
            )
        except Exception as e:
            _logger.warning(f"Failed to send invoice email for {invoice.name}: {e}")

    def action_cancel(self):
        """Cancel the wizard"""
        return {'type': 'ir.actions.act_window_close'}

    @api.model
    def create_renewal_invoices_cron(self):
        """Cron job to create renewal invoices automatically"""
        today = fields.Date.today()
        
        # Find subscriptions that need renewal invoices
        subscriptions = self.env['ams.member.subscription'].search([
            ('state', '=', 'active'),
            ('auto_renew', '=', True),
            ('renewal_date', '<=', today),
            ('renewal_sent', '=', False)
        ])
        
        if subscriptions:
            wizard = self.create({
                'invoice_type': 'membership_renewal',
                'selection_method': 'manual',
                'subscription_ids': [(6, 0, subscriptions.ids)],
                'auto_post_invoices': True,
                'send_by_email': True,
            })
            
            # Set default email template
            template = self.env.ref(
                'ams_subscriptions.email_template_renewal_invoice',
                raise_if_not_found=False
            )
            if template:
                wizard.email_template_id = template.id
            
            # Process the invoices
            wizard.action_create_invoices()
            
            # Mark renewals as sent
            subscriptions.write({'renewal_sent': True})
            
            return len(subscriptions)
        
        return 0