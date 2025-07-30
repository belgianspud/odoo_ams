from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from dateutil.relativedelta import relativedelta
import logging

_logger = logging.getLogger(__name__)


class BulkSubscriptionWizard(models.TransientModel):
    _name = 'ams.bulk.subscription.wizard'
    _description = 'Bulk Subscription Operations Wizard'

    # Operation Type
    operation_type = fields.Selection([
        ('create', 'Create Subscriptions'),
        ('update', 'Update Subscriptions'),
        ('cancel', 'Cancel Subscriptions'),
        ('suspend', 'Suspend Subscriptions'),
        ('reactivate', 'Reactivate Subscriptions'),
        ('change_chapter', 'Change Chapter'),
        ('change_membership_type', 'Change Membership Type'),
        ('apply_discount', 'Apply Discount'),
        ('send_notifications', 'Send Notifications')
    ], string='Operation', default='create', required=True)
    
    # Selection Criteria
    selection_method = fields.Selection([
        ('manual', 'Manual Selection'),
        ('criteria', 'By Criteria'),
        ('import', 'Import from File')
    ], string='Selection Method', default='manual', required=True)
    
    # Manual Selection
    partner_ids = fields.Many2many(
        'res.partner',
        string='Members',
        domain=[('is_company', '=', False)]
    )
    
    subscription_ids = fields.Many2many(
        'ams.member.subscription',
        string='Existing Subscriptions'
    )
    
    # Criteria Selection
    membership_type_ids = fields.Many2many(
        'ams.membership.type',
        'bulk_wizard_membership_type_rel',
        string='Membership Types'
    )
    
    chapter_ids = fields.Many2many(
        'ams.chapter',
        'bulk_wizard_chapter_rel',
        string='Chapters'
    )
    
    subscription_states = fields.Selection([
        ('all', 'All States'),
        ('draft', 'Draft'),
        ('pending_approval', 'Pending Approval'),
        ('active', 'Active'),
        ('pending_renewal', 'Pending Renewal'),
        ('expired', 'Expired'),
        ('lapsed', 'Lapsed'),
        ('cancelled', 'Cancelled'),
        ('suspended', 'Suspended')
    ], string='Subscription States', default='all')
    
    date_filter_type = fields.Selection([
        ('none', 'No Date Filter'),
        ('start_date', 'Start Date'),
        ('end_date', 'End Date'),
        ('created_date', 'Created Date')
    ], string='Date Filter', default='none')
    
    date_from = fields.Date(string='Date From')
    date_to = fields.Date(string='Date To')
    
    # File Import
    import_file = fields.Binary(
        string='Import File',
        help="CSV file with member information"
    )
    
    import_filename = fields.Char(string='Filename')
    
    # Create Operation Fields
    new_membership_type_id = fields.Many2one(
        'ams.membership.type',
        string='Membership Type'
    )
    
    new_chapter_id = fields.Many2one(
        'ams.chapter',
        string='Chapter'
    )
    
    start_date = fields.Date(
        string='Start Date',
        default=fields.Date.context_today
    )
    
    # Update Operation Fields
    update_start_date = fields.Date(string='New Start Date')
    update_end_date = fields.Date(string='New End Date')
    update_chapter_id = fields.Many2one('ams.chapter', string='New Chapter')
    update_membership_type_id = fields.Many2one('ams.membership.type', string='New Membership Type')
    
    # Pricing Options
    pricing_option = fields.Selection([
        ('standard', 'Standard Pricing'),
        ('custom', 'Custom Price'),
        ('discount', 'Apply Discount')
    ], string='Pricing Option', default='standard')
    
    custom_price = fields.Float(
        string='Custom Price',
        digits='Product Price'
    )
    
    discount_type = fields.Selection([
        ('percentage', 'Percentage'),
        ('fixed', 'Fixed Amount')
    ], string='Discount Type', default='percentage')
    
    discount_percentage = fields.Float(
        string='Discount %',
        digits='Discount'
    )
    
    discount_amount = fields.Float(
        string='Discount Amount',
        digits='Product Price'
    )
    
    # Notification Options
    send_notifications = fields.Boolean(
        string='Send Notifications',
        default=True
    )
    
    notification_template_id = fields.Many2one(
        'mail.template',
        string='Email Template',
        domain=[('model', '=', 'ams.member.subscription')]
    )
    
    custom_message = fields.Html(
        string='Custom Message'
    )
    
    # Processing Options
    auto_confirm_orders = fields.Boolean(
        string='Auto-Confirm Orders',
        default=True
    )
    
    auto_create_invoices = fields.Boolean(
        string='Auto-Create Invoices',
        default=False
    )
    
    batch_size = fields.Integer(
        string='Batch Size',
        default=100,
        help="Number of records to process at once"
    )
    
    # Results
    target_count = fields.Integer(
        string='Target Records',
        compute='_compute_target_count'
    )
    
    preview_data = fields.Html(
        string='Preview',
        compute='_compute_preview_data'
    )
    
    # Processing Results
    processing_log = fields.Html(
        string='Processing Log',
        readonly=True
    )
    
    success_count = fields.Integer(
        string='Successful Operations',
        readonly=True
    )
    
    error_count = fields.Integer(
        string='Failed Operations',
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

    @api.depends('selection_method', 'partner_ids', 'subscription_ids', 
                 'membership_type_ids', 'chapter_ids', 'subscription_states',
                 'date_filter_type', 'date_from', 'date_to')
    def _compute_target_count(self):
        """Compute number of target records"""
        for wizard in self:
            targets = wizard._get_target_records()
            wizard.target_count = len(targets)

    @api.depends('target_count')
    def _compute_preview_data(self):
        """Compute preview data"""
        for wizard in self:
            if wizard.target_count == 0:
                wizard.preview_data = "<p>No records found matching the criteria.</p>"
                continue
            
            targets = wizard._get_target_records()
            wizard.preview_data = wizard._generate_preview_html(targets)

    @api.onchange('operation_type')
    def _onchange_operation_type(self):
        """Update available fields based on operation type"""
        if self.operation_type in ['create']:
            self.selection_method = 'manual'
        elif self.operation_type in ['update', 'cancel', 'suspend', 'reactivate', 'send_notifications']:
            if self.selection_method == 'import':
                self.selection_method = 'criteria'

    @api.onchange('selection_method')
    def _onchange_selection_method(self):
        """Clear fields when selection method changes"""
        if self.selection_method == 'manual':
            self.membership_type_ids = [(5, 0, 0)]
            self.chapter_ids = [(5, 0, 0)]
        elif self.selection_method == 'criteria':
            self.partner_ids = [(5, 0, 0)]
            self.subscription_ids = [(5, 0, 0)]
        elif self.selection_method == 'import':
            self.partner_ids = [(5, 0, 0)]
            self.subscription_ids = [(5, 0, 0)]
            self.membership_type_ids = [(5, 0, 0)]
            self.chapter_ids = [(5, 0, 0)]

    @api.constrains('batch_size')
    def _check_batch_size(self):
        """Validate batch size"""
        for wizard in self:
            if wizard.batch_size <= 0:
                raise ValidationError(_("Batch size must be greater than 0."))

    @api.constrains('discount_percentage')
    def _check_discount_percentage(self):
        """Validate discount percentage"""
        for wizard in self:
            if wizard.discount_percentage < 0 or wizard.discount_percentage > 100:
                raise ValidationError(_("Discount percentage must be between 0 and 100."))

    def _get_target_records(self):
        """Get target records based on operation and selection criteria"""
        self.ensure_one()
        
        if self.operation_type == 'create':
            return self._get_target_partners()
        else:
            return self._get_target_subscriptions()

    def _get_target_partners(self):
        """Get target partners for create operations"""
        self.ensure_one()
        
        if self.selection_method == 'manual':
            return self.partner_ids
        
        elif self.selection_method == 'import':
            return self._get_partners_from_import()
        
        elif self.selection_method == 'criteria':
            domain = [('is_company', '=', False)]
            
            # Add additional criteria here if needed
            # For now, return empty for criteria-based partner selection
            return self.env['res.partner'].browse([])
        
        return self.env['res.partner'].browse([])

    def _get_target_subscriptions(self):
        """Get target subscriptions for update/cancel operations"""
        self.ensure_one()
        
        if self.selection_method == 'manual':
            return self.subscription_ids
        
        elif self.selection_method == 'criteria':
            domain = []
            
            # Filter by membership types
            membership_type_ids = self._get_record_ids(self.membership_type_ids)
            if membership_type_ids:
                domain.append(('membership_type_id', 'in', membership_type_ids))
            
            # Filter by chapters
            chapter_ids = self._get_record_ids(self.chapter_ids)
            if chapter_ids:
                domain.append(('chapter_id', 'in', chapter_ids))
            
            # Filter by states
            if self.subscription_states != 'all':
                domain.append(('state', '=', self.subscription_states))
            
            # Filter by dates
            if self.date_filter_type != 'none' and self.date_from:
                if self.date_filter_type == 'start_date':
                    domain.append(('start_date', '>=', self.date_from))
                elif self.date_filter_type == 'end_date':
                    domain.append(('end_date', '>=', self.date_from))
                elif self.date_filter_type == 'created_date':
                    domain.append(('create_date', '>=', self.date_from))
            
            if self.date_filter_type != 'none' and self.date_to:
                if self.date_filter_type == 'start_date':
                    domain.append(('start_date', '<=', self.date_to))
                elif self.date_filter_type == 'end_date':
                    domain.append(('end_date', '<=', self.date_to))
                elif self.date_filter_type == 'created_date':
                    domain.append(('create_date', '<=', self.date_to))
            
            return self.env['ams.member.subscription'].search(domain)
        
        return self.env['ams.member.subscription'].browse([])

    def _get_partners_from_import(self):
        """Get partners from imported file"""
        # This would implement CSV parsing logic
        # For now, return empty
        return self.env['res.partner'].browse([])

    def _generate_preview_html(self, targets):
        """Generate HTML preview of target records"""
        self.ensure_one()
        
        preview_html = "<table class='table table-sm'>"
        
        if self.operation_type == 'create':
            preview_html += "<thead><tr><th>Partner</th><th>Email</th><th>Membership Type</th><th>Chapter</th><th>Price</th></tr></thead>"
            preview_html += "<tbody>"
            
            for partner in targets[:10]:  # Show max 10 for preview
                try:
                    price = self._calculate_price_for_partner(partner)
                    membership_type_name = self.new_membership_type_id.name if self.new_membership_type_id else 'Not Set'
                    chapter_name = self.new_chapter_id.name if self.new_chapter_id else 'Not Set'
                    
                    preview_html += f"""
                    <tr>
                        <td>{partner.name}</td>
                        <td>{partner.email or 'No Email'}</td>
                        <td>{membership_type_name}</td>
                        <td>{chapter_name}</td>
                        <td>{price:.2f}</td>
                    </tr>
                    """
                except Exception as e:
                    _logger.error(f"Error in preview generation for partner {partner.id}: {e}")
                    continue
        
        else:  # Update operations
            preview_html += "<thead><tr><th>Member</th><th>Membership Type</th><th>Chapter</th><th>State</th><th>Operation</th></tr></thead>"
            preview_html += "<tbody>"
            
            for subscription in targets[:10]:  # Show max 10 for preview
                try:
                    member_name = subscription.partner_id.name if subscription.partner_id else 'Unknown'
                    membership_name = subscription.membership_type_id.name if subscription.membership_type_id else 'Unknown'
                    chapter_name = subscription.chapter_id.name if subscription.chapter_id else 'None'
                    
                    preview_html += f"""
                    <tr>
                        <td>{member_name}</td>
                        <td>{membership_name}</td>
                        <td>{chapter_name}</td>
                        <td>{subscription.state}</td>
                        <td>{self.operation_type.title()}</td>
                    </tr>
                    """
                except Exception as e:
                    _logger.error(f"Error in preview generation for subscription {subscription.id}: {e}")
                    continue
        
        if len(targets) > 10:
            preview_html += f"<tr><td colspan='5'><em>... and {len(targets) - 10} more</em></td></tr>"
        
        preview_html += "</tbody></table>"
        return preview_html

    def _calculate_price_for_partner(self, partner):
        """Calculate price for a partner"""
        self.ensure_one()
        
        if self.pricing_option == 'custom':
            return self.custom_price
        
        # Get base price from membership type
        base_price = 0.0
        if self.new_membership_type_id:
            base_price = self.new_membership_type_id.price
        
        if self.pricing_option == 'discount':
            if self.discount_type == 'percentage':
                discount = base_price * (self.discount_percentage / 100)
                return base_price - discount
            else:  # fixed amount
                return max(0, base_price - self.discount_amount)
        
        return base_price

    def action_preview(self):
        """Preview the operation"""
        self.ensure_one()
        
        targets = self._get_target_records()
        
        if not targets:
            raise UserError(_("No records found matching the criteria."))
        
        # Validate operation requirements
        if self.operation_type == 'create' and not self.new_membership_type_id:
            raise UserError(_("Membership type is required for create operations."))
        
        # Force recompute of preview
        self._compute_preview_data()
        
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'ams.bulk.subscription.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
            'context': {'show_preview': True}
        }

    def action_process(self):
        """Process the bulk operation"""
        self.ensure_one()
        
        targets = self._get_target_records()
        
        if not targets:
            raise UserError(_("No records found matching the criteria."))
        
        # Validate operation requirements
        self._validate_operation_requirements()
        
        # Process in batches
        processing_log = []
        success_count = 0
        error_count = 0
        
        # Split targets into batches
        batch_size = self.batch_size
        batches = [targets[i:i + batch_size] for i in range(0, len(targets), batch_size)]
        
        for batch_num, batch in enumerate(batches, 1):
            processing_log.append(f"<h5>Processing Batch {batch_num}/{len(batches)}</h5>")
            
            batch_success, batch_errors, batch_log = self._process_batch(batch)
            
            success_count += batch_success
            error_count += batch_errors
            processing_log.extend(batch_log)
            
            # Commit after each batch to avoid timeout
            self.env.cr.commit()
        
        # Update wizard with results
        self.processing_log = '<br/>'.join(processing_log)
        self.success_count = success_count
        self.error_count = error_count
        
        message = _("Operation completed: %s successful, %s errors") % (success_count, error_count)
        
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'ams.bulk.subscription.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'show_results': True,
                'result_message': message
            }
        }

    def _validate_operation_requirements(self):
        """Validate requirements for the operation"""
        self.ensure_one()
        
        if self.operation_type == 'create':
            if not self.new_membership_type_id:
                raise UserError(_("Membership type is required for create operations."))
        
        elif self.operation_type == 'change_membership_type':
            if not self.update_membership_type_id:
                raise UserError(_("New membership type is required."))
        
        elif self.operation_type == 'change_chapter':
            if not self.update_chapter_id:
                raise UserError(_("New chapter is required."))
        
        elif self.operation_type == 'send_notifications':
            if not self.notification_template_id:
                raise UserError(_("Email template is required for sending notifications."))

    def _process_batch(self, batch):
        """Process a batch of records"""
        self.ensure_one()
        
        success_count = 0
        error_count = 0
        batch_log = []
        
        for record in batch:
            try:
                if self.operation_type == 'create':
                    self._create_subscription(record)
                    success_count += 1
                    batch_log.append(f"✓ Created subscription for {record.name}")
                
                elif self.operation_type == 'update':
                    self._update_subscription(record)
                    success_count += 1
                    batch_log.append(f"✓ Updated subscription for {record.partner_id.name}")
                
                elif self.operation_type == 'cancel':
                    record.action_cancel()
                    success_count += 1
                    batch_log.append(f"✓ Cancelled subscription for {record.partner_id.name}")
                
                elif self.operation_type == 'suspend':
                    record.action_suspend()
                    success_count += 1
                    batch_log.append(f"✓ Suspended subscription for {record.partner_id.name}")
                
                elif self.operation_type == 'reactivate':
                    record.action_reactivate()
                    success_count += 1
                    batch_log.append(f"✓ Reactivated subscription for {record.partner_id.name}")
                
                elif self.operation_type == 'change_chapter':
                    record.chapter_id = self.update_chapter_id.id
                    success_count += 1
                    batch_log.append(f"✓ Changed chapter for {record.partner_id.name}")
                
                elif self.operation_type == 'change_membership_type':
                    record.membership_type_id = self.update_membership_type_id.id
                    success_count += 1
                    batch_log.append(f"✓ Changed membership type for {record.partner_id.name}")
                
                elif self.operation_type == 'send_notifications':
                    self._send_notification(record)
                    success_count += 1
                    batch_log.append(f"✓ Sent notification to {record.partner_id.name}")
                
            except Exception as e:
                error_count += 1
                record_name = getattr(record, 'name', 'Unknown')
                batch_log.append(f"✗ Failed for {record_name}: {str(e)}")
                _logger.error(f"Batch processing failed for record {record.id}: {e}")
        
        return success_count, error_count, batch_log

    def _create_subscription(self, partner):
        """Create subscription for a partner"""
        self.ensure_one()
        
        price = self._calculate_price_for_partner(partner)
        
        subscription_vals = {
            'partner_id': partner.id,
            'membership_type_id': self.new_membership_type_id.id,
            'chapter_id': self.new_chapter_id.id if self.new_chapter_id else False,
            'start_date': self.start_date,
            'unit_price': price,
        }
        
        # Apply discount if applicable
        if self.pricing_option == 'discount':
            if self.discount_type == 'percentage':
                subscription_vals['discount_percent'] = self.discount_percentage
        
        subscription = self.env['ams.member.subscription'].create(subscription_vals)
        
        # Create sale order if requested
        if self.auto_confirm_orders:
            try:
                subscription._create_sale_order()
                if subscription.sale_order_id:
                    subscription.sale_order_id.action_confirm()
                    
                    if self.auto_create_invoices:
                        subscription.sale_order_id._create_invoices()
            except Exception as e:
                _logger.warning(f"Failed to create/confirm order for subscription {subscription.id}: {e}")
        
        # Send notification if requested
        if self.send_notifications:
            self._send_notification(subscription)
        
        return subscription

    def _update_subscription(self, subscription):
        """Update a subscription"""
        self.ensure_one()
        
        update_vals = {}
        
        if self.update_start_date:
            update_vals['start_date'] = self.update_start_date
        
        if self.update_end_date:
            update_vals['end_date'] = self.update_end_date
        
        if self.update_chapter_id:
            update_vals['chapter_id'] = self.update_chapter_id.id
        
        if self.update_membership_type_id:
            update_vals['membership_type_id'] = self.update_membership_type_id.id
        
        if update_vals:
            subscription.write(update_vals)

    def _send_notification(self, subscription):
        """Send notification for a subscription"""
        self.ensure_one()
        
        if not self.notification_template_id:
            return
        
        try:
            email_values = {}
            if self.custom_message:
                email_values['body_html'] = self.custom_message
            
            self.notification_template_id.send_mail(
                subscription.id,
                force_send=True,
                email_values=email_values
            )
        except Exception as e:
            _logger.warning(f"Failed to send notification for subscription {subscription.id}: {e}")

    def action_close(self):
        """Close the wizard"""
        return {'type': 'ir.actions.act_window_close'}