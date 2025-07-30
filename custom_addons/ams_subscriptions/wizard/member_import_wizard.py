from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
import csv
import io
import base64
import logging

_logger = logging.getLogger(__name__)


class MemberImportWizard(models.TransientModel):
    _name = 'ams.member.import.wizard'
    _description = 'Member Import Wizard'

    # Import Settings
    import_type = fields.Selection([
        ('new_members', 'New Members'),
        ('update_existing', 'Update Existing Members'),
        ('new_subscriptions', 'New Subscriptions'),
        ('update_subscriptions', 'Update Subscriptions'),
        ('mixed', 'Mixed Import')
    ], string='Import Type', required=True, default='new_members')

    # File Upload
    import_file = fields.Binary(
        string='Import File',
        required=True,
        help="CSV file containing member data"
    )
    
    import_filename = fields.Char(
        string='Filename',
        help="Name of the uploaded file"
    )
    
    file_encoding = fields.Selection([
        ('utf-8', 'UTF-8'),
        ('latin1', 'Latin-1'),
        ('cp1252', 'Windows-1252')
    ], string='File Encoding', default='utf-8', required=True)
    
    delimiter = fields.Selection([
        (',', 'Comma (,)'),
        (';', 'Semicolon (;)'),
        ('\t', 'Tab'),
        ('|', 'Pipe (|)')
    ], string='CSV Delimiter', default=',', required=True)
    
    has_header = fields.Boolean(
        string='File has Header Row',
        default=True,
        help="Check if the first row contains column headers"
    )

    # Field Mapping
    mapping_ids = fields.One2many(
        'ams.member.import.mapping',
        'wizard_id',
        string='Field Mappings'
    )
    
    # Default Values
    default_membership_type_id = fields.Many2one(
        'ams.membership.type',
        string='Default Membership Type',
        help="Default membership type for new subscriptions"
    )
    
    default_chapter_id = fields.Many2one(
        'ams.chapter',
        string='Default Chapter',
        help="Default chapter for new subscriptions"
    )
    
    default_start_date = fields.Date(
        string='Default Start Date',
        default=fields.Date.context_today,
        help="Default start date for new subscriptions"
    )
    
    auto_approve_subscriptions = fields.Boolean(
        string='Auto-Approve Subscriptions',
        default=False,
        help="Automatically approve created subscriptions"
    )

    # Duplicate Handling
    duplicate_handling = fields.Selection([
        ('skip', 'Skip Duplicates'),
        ('update', 'Update Existing'),
        ('create_new', 'Create New Record'),
        ('ask', 'Ask for Each Duplicate')
    ], string='Duplicate Handling', default='skip', required=True)
    
    match_field = fields.Selection([
        ('email', 'Email Address'),
        ('membership_number', 'Membership Number'),
        ('name_email', 'Name + Email'),
        ('external_id', 'External ID')
    ], string='Match Field', default='email', required=True)

    # Validation Options
    validate_emails = fields.Boolean(
        string='Validate Email Addresses',
        default=True
    )
    
    validate_required_fields = fields.Boolean(
        string='Validate Required Fields',
        default=True
    )
    
    skip_invalid_records = fields.Boolean(
        string='Skip Invalid Records',
        default=True,
        help="Skip records that fail validation instead of stopping import"
    )

    # Processing Options
    batch_size = fields.Integer(
        string='Batch Size',
        default=100,
        help="Number of records to process at once"
    )
    
    create_partners = fields.Boolean(
        string='Create Missing Partners',
        default=True,
        help="Create partner records for new members"
    )
    
    create_subscriptions = fields.Boolean(
        string='Create Subscriptions',
        default=True,
        help="Create subscription records along with members"
    )
    
    send_welcome_emails = fields.Boolean(
        string='Send Welcome Emails',
        default=False,
        help="Send welcome emails to new members"
    )
    
    welcome_template_id = fields.Many2one(
        'mail.template',
        string='Welcome Email Template',
        domain=[('model', '=', 'res.partner')]
    )

    # Preview and Validation
    file_data = fields.Text(
        string='File Data',
        readonly=True,
        help="Parsed file data for preview"
    )
    
    preview_data = fields.Html(
        string='Data Preview',
        compute='_compute_preview_data'
    )
    
    validation_results = fields.Html(
        string='Validation Results',
        readonly=True
    )
    
    total_records = fields.Integer(
        string='Total Records',
        readonly=True
    )
    
    valid_records = fields.Integer(
        string='Valid Records',
        readonly=True
    )
    
    invalid_records = fields.Integer(
        string='Invalid Records',
        readonly=True
    )

    # Import Results
    import_log = fields.Html(
        string='Import Log',
        readonly=True
    )
    
    records_created = fields.Integer(
        string='Records Created',
        readonly=True
    )
    
    records_updated = fields.Integer(
        string='Records Updated',
        readonly=True
    )
    
    records_skipped = fields.Integer(
        string='Records Skipped',
        readonly=True
    )
    
    records_failed = fields.Integer(
        string='Records Failed',
        readonly=True
    )
    
    import_completed = fields.Boolean(
        string='Import Completed',
        default=False,
        readonly=True
    )

    @api.depends('file_data', 'has_header')
    def _compute_preview_data(self):
        """Compute preview data from file"""
        for wizard in self:
            if not wizard.file_data:
                wizard.preview_data = "<p>Please upload a file to see preview</p>"
                continue
            
            try:
                lines = wizard.file_data.strip().split('\n')
                if not lines:
                    wizard.preview_data = "<p>File appears to be empty</p>"
                    continue
                
                # Show first 5 rows
                preview_lines = lines[:5]
                
                preview_html = "<table class='table table-sm table-bordered'>"
                
                for i, line in enumerate(preview_lines):
                    row_class = "table-info" if (i == 0 and wizard.has_header) else ""
                    cells = line.split(wizard.delimiter)
                    
                    preview_html += f"<tr class='{row_class}'>"
                    for cell in cells:
                        preview_html += f"<td>{cell[:50]}{'...' if len(cell) > 50 else ''}</td>"
                    preview_html += "</tr>"
                
                if len(lines) > 5:
                    preview_html += f"<tr><td colspan='{len(preview_lines[0].split(wizard.delimiter))}'><em>... and {len(lines) - 5} more rows</em></td></tr>"
                
                preview_html += "</table>"
                wizard.preview_data = preview_html
                
            except Exception as e:
                wizard.preview_data = f"<p class='text-danger'>Error parsing file: {str(e)}</p>"

    @api.onchange('import_file', 'file_encoding', 'delimiter')
    def _onchange_import_file(self):
        """Parse uploaded file"""
        if not self.import_file:
            self.file_data = ''
            self.mapping_ids = [(5, 0, 0)]
            return
        
        try:
            # Decode file
            file_content = base64.b64decode(self.import_file)
            decoded_content = file_content.decode(self.file_encoding)
            
            # Store raw data
            self.file_data = decoded_content
            
            # Parse CSV to get headers
            csv_reader = csv.reader(io.StringIO(decoded_content), delimiter=self.delimiter)
            
            if self.has_header:
                headers = next(csv_reader, [])
                self._create_field_mappings(headers)
            
            # Count total records
            lines = decoded_content.strip().split('\n')
            self.total_records = len(lines) - (1 if self.has_header else 0)
            
        except Exception as e:
            self.file_data = ''
            self.total_records = 0
            raise UserError(_("Error reading file: %s") % str(e))

    def _create_field_mappings(self, headers):
        """Create field mappings based on CSV headers"""
        self.mapping_ids = [(5, 0, 0)]  # Clear existing mappings
        
        # Standard field mappings
        field_mappings = {
            'name': ['name', 'full_name', 'member_name', 'first_name last_name'],
            'first_name': ['first_name', 'fname'],
            'last_name': ['last_name', 'surname', 'lname'],
            'email': ['email', 'email_address', 'e_mail'],
            'phone': ['phone', 'telephone', 'mobile'],
            'street': ['address', 'street', 'address1'],
            'street2': ['address2', 'street2'],
            'city': ['city', 'town'],
            'zip': ['zip', 'postal_code', 'postcode'],
            'membership_number': ['membership_number', 'member_id', 'member_number'],
            'membership_type': ['membership_type', 'type', 'category'],
            'chapter': ['chapter', 'branch', 'location'],
            'start_date': ['start_date', 'join_date', 'member_since'],
            'end_date': ['end_date', 'expiry_date', 'expires'],
        }
        
        mappings_to_create = []
        
        for i, header in enumerate(headers):
            header_lower = header.lower().strip()
            
            # Find best match
            odoo_field = None
            for field, variants in field_mappings.items():
                if header_lower in [v.lower() for v in variants]:
                    odoo_field = field
                    break
            
            mapping_vals = {
                'sequence': i + 1,
                'csv_field': header,
                'odoo_field': odoo_field,
                'wizard_id': self.id,
            }
            mappings_to_create.append((0, 0, mapping_vals))
        
        self.mapping_ids = mappings_to_create

    def action_validate_data(self):
        """Validate the import data"""
        self.ensure_one()
        
        if not self.import_file:
            raise UserError(_("Please upload a file first"))
        
        try:
            validation_results = self._validate_import_data()
            
            self.validation_results = self._format_validation_results(validation_results)
            self.valid_records = validation_results.get('valid_count', 0)
            self.invalid_records = validation_results.get('invalid_count', 0)
            
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'ams.member.import.wizard',
                'res_id': self.id,
                'view_mode': 'form',
                'target': 'new',
                'context': {'show_validation': True}
            }
            
        except Exception as e:
            raise UserError(_("Validation failed: %s") % str(e))

    def _validate_import_data(self):
        """Validate import data and return results"""
        if not self.file_data:
            return {'valid_count': 0, 'invalid_count': 0, 'errors': []}
        
        # Parse CSV data
        csv_reader = csv.reader(io.StringIO(self.file_data), delimiter=self.delimiter)
        
        if self.has_header:
            headers = next(csv_reader, [])
        
        # Get field mappings
        field_map = {m.csv_field: m.odoo_field for m in self.mapping_ids if m.odoo_field}
        
        valid_count = 0
        invalid_count = 0
        errors = []
        
        for row_num, row in enumerate(csv_reader, start=2 if self.has_header else 1):
            try:
                # Create record dict
                record_data = {}
                for i, value in enumerate(row):
                    if i < len(headers):
                        csv_field = headers[i]
                        odoo_field = field_map.get(csv_field)
                        if odoo_field:
                            record_data[odoo_field] = value.strip() if value else ''
                
                # Validate record
                validation_errors = self._validate_record(record_data, row_num)
                
                if validation_errors:
                    invalid_count += 1
                    errors.extend(validation_errors)
                else:
                    valid_count += 1
                    
            except Exception as e:
                invalid_count += 1
                errors.append(f"Row {row_num}: {str(e)}")
        
        return {
            'valid_count': valid_count,
            'invalid_count': invalid_count,
            'errors': errors
        }

    def _validate_record(self, record_data, row_num):
        """Validate a single record"""
        errors = []
        
        # Check required fields
        if self.validate_required_fields:
            if not record_data.get('name') and not (record_data.get('first_name') and record_data.get('last_name')):
                errors.append(f"Row {row_num}: Name is required")
            
            if self.import_type in ['new_members', 'mixed'] and not record_data.get('email'):
                errors.append(f"Row {row_num}: Email is required for new members")
        
        # Validate email format
        if self.validate_emails and record_data.get('email'):
            email = record_data['email']
            if '@' not in email or '.' not in email.split('@')[-1]:
                errors.append(f"Row {row_num}: Invalid email format: {email}")
        
        # Check for duplicates
        if record_data.get('email'):
            existing = self._find_existing_record(record_data)
            if existing and self.duplicate_handling == 'skip':
                # This will be skipped, not an error
                pass
        
        return errors

    def _find_existing_record(self, record_data):
        """Find existing record based on match field"""
        domain = []
        
        if self.match_field == 'email' and record_data.get('email'):
            domain = [('email', '=', record_data['email'])]
        elif self.match_field == 'membership_number' and record_data.get('membership_number'):
            domain = [('membership_number', '=', record_data['membership_number'])]
        elif self.match_field == 'name_email':
            if record_data.get('name') and record_data.get('email'):
                domain = [('name', '=', record_data['name']), ('email', '=', record_data['email'])]
        
        if domain:
            return self.env['res.partner'].search(domain, limit=1)
        
        return None

    def _format_validation_results(self, results):
        """Format validation results for display"""
        html = f"<div class='alert alert-info'>"
        html += f"<h5>Validation Summary</h5>"
        html += f"<p>Valid Records: <strong>{results['valid_count']}</strong></p>"
        html += f"<p>Invalid Records: <strong>{results['invalid_count']}</strong></p>"
        html += f"</div>"
        
        if results['errors']:
            html += f"<div class='alert alert-warning'>"
            html += f"<h5>Validation Errors</h5>"
            html += f"<ul>"
            for error in results['errors'][:20]:  # Show max 20 errors
                html += f"<li>{error}</li>"
            if len(results['errors']) > 20:
                html += f"<li><em>... and {len(results['errors']) - 20} more errors</em></li>"
            html += f"</ul>"
            html += f"</div>"
        
        return html

    def action_import_data(self):
        """Import the validated data"""
        self.ensure_one()
        
        if not self.import_file:
            raise UserError(_("Please upload a file first"))
        
        if not self.valid_records and self.validate_required_fields:
            raise UserError(_("No valid records found. Please validate data first."))
        
        try:
            # Process the import
            import_results = self._process_import()
            
            # Update wizard with results
            self.import_log = self._format_import_results(import_results)
            self.records_created = import_results.get('created', 0)
            self.records_updated = import_results.get('updated', 0)
            self.records_skipped = import_results.get('skipped', 0)
            self.records_failed = import_results.get('failed', 0)
            self.import_completed = True
            
            message = _("Import completed: %s created, %s updated, %s skipped, %s failed") % (
                self.records_created, self.records_updated, self.records_skipped, self.records_failed
            )
            
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'ams.member.import.wizard',
                'res_id': self.id,
                'view_mode': 'form',
                'target': 'new',
                'context': {
                    'show_results': True,
                    'result_message': message
                }
            }
            
        except Exception as e:
            _logger.error(f"Import failed: {e}")
            raise UserError(_("Import failed: %s") % str(e))

    def _process_import(self):
        """Process the actual import"""
        if not self.file_data:
            return {'created': 0, 'updated': 0, 'skipped': 0, 'failed': 0, 'log': []}
        
        # Parse CSV data
        csv_reader = csv.reader(io.StringIO(self.file_data), delimiter=self.delimiter)
        
        if self.has_header:
            headers = next(csv_reader, [])
        
        # Get field mappings
        field_map = {m.csv_field: m.odoo_field for m in self.mapping_ids if m.odoo_field}
        
        # Process in batches
        created_count = 0
        updated_count = 0
        skipped_count = 0
        failed_count = 0
        import_log = []
        
        batch = []
        batch_num = 0
        
        for row_num, row in enumerate(csv_reader, start=2 if self.has_header else 1):
            try:
                # Create record dict
                record_data = {}
                for i, value in enumerate(row):
                    if i < len(headers):
                        csv_field = headers[i]
                        odoo_field = field_map.get(csv_field)
                        if odoo_field:
                            record_data[odoo_field] = value.strip() if value else ''
                
                batch.append((row_num, record_data))
                
                # Process batch when full
                if len(batch) >= self.batch_size:
                    batch_results = self._process_batch(batch, batch_num)
                    created_count += batch_results['created']
                    updated_count += batch_results['updated']
                    skipped_count += batch_results['skipped']
                    failed_count += batch_results['failed']
                    import_log.extend(batch_results['log'])
                    
                    batch = []
                    batch_num += 1
                    
                    # Commit after each batch
                    self.env.cr.commit()
                    
            except Exception as e:
                failed_count += 1
                import_log.append(f"Row {row_num}: Failed to process - {str(e)}")
        
        # Process remaining records
        if batch:
            batch_results = self._process_batch(batch, batch_num)
            created_count += batch_results['created']
            updated_count += batch_results['updated']
            skipped_count += batch_results['skipped']
            failed_count += batch_results['failed']
            import_log.extend(batch_results['log'])
        
        return {
            'created': created_count,
            'updated': updated_count,
            'skipped': skipped_count,
            'failed': failed_count,
            'log': import_log
        }

    def _process_batch(self, batch, batch_num):
        """Process a batch of records"""
        results = {'created': 0, 'updated': 0, 'skipped': 0, 'failed': 0, 'log': []}
        
        for row_num, record_data in batch:
            try:
                # Skip if validation fails and skip_invalid_records is True
                if self.skip_invalid_records:
                    validation_errors = self._validate_record(record_data, row_num)
                    if validation_errors:
                        results['skipped'] += 1
                        results['log'].append(f"Row {row_num}: Skipped due to validation errors")
                        continue
                
                # Check for existing record
                existing_partner = self._find_existing_record(record_data)
                
                if existing_partner:
                    if self.duplicate_handling == 'skip':
                        results['skipped'] += 1
                        results['log'].append(f"Row {row_num}: Skipped duplicate - {record_data.get('name', 'Unknown')}")
                        continue
                    elif self.duplicate_handling == 'update':
                        partner = self._update_partner(existing_partner, record_data)
                        results['updated'] += 1
                        results['log'].append(f"Row {row_num}: Updated - {partner.name}")
                    else:  # create_new
                        partner = self._create_partner(record_data)
                        results['created'] += 1
                        results['log'].append(f"Row {row_num}: Created new - {partner.name}")
                else:
                    # Create new partner
                    partner = self._create_partner(record_data)
                    results['created'] += 1
                    results['log'].append(f"Row {row_num}: Created - {partner.name}")
                
                # Create subscription if requested
                if self.create_subscriptions and partner:
                    subscription = self._create_subscription(partner, record_data)
                    if subscription:
                        results['log'].append(f"Row {row_num}: Created subscription for {partner.name}")
                
                # Send welcome email if requested
                if self.send_welcome_emails and self.welcome_template_id and partner:
                    self._send_welcome_email(partner)
                    
            except Exception as e:
                results['failed'] += 1
                results['log'].append(f"Row {row_num}: Failed - {str(e)}")
                _logger.error(f"Import batch processing failed for row {row_num}: {e}")
        
        return results

    def _create_partner(self, record_data):
        """Create a new partner"""
        partner_vals = {
            'is_company': False,
            'supplier_rank': 0,
            'customer_rank': 1,
        }
        
        # Map fields
        if record_data.get('name'):
            partner_vals['name'] = record_data['name']
        elif record_data.get('first_name') and record_data.get('last_name'):
            partner_vals['name'] = f"{record_data['first_name']} {record_data['last_name']}"
        
        if record_data.get('email'):
            partner_vals['email'] = record_data['email']
        
        if record_data.get('phone'):
            partner_vals['phone'] = record_data['phone']
        
        if record_data.get('street'):
            partner_vals['street'] = record_data['street']
        
        if record_data.get('street2'):
            partner_vals['street2'] = record_data['street2']
        
        if record_data.get('city'):
            partner_vals['city'] = record_data['city']
        
        if record_data.get('zip'):
            partner_vals['zip'] = record_data['zip']
        
        if record_data.get('membership_number'):
            partner_vals['membership_number'] = record_data['membership_number']
        
        return self.env['res.partner'].create(partner_vals)

    def _update_partner(self, partner, record_data):
        """Update existing partner"""
        update_vals = {}
        
        # Update fields that have values
        if record_data.get('phone') and record_data['phone'] != partner.phone:
            update_vals['phone'] = record_data['phone']
        
        if record_data.get('street') and record_data['street'] != partner.street:
            update_vals['street'] = record_data['street']
        
        if record_data.get('city') and record_data['city'] != partner.city:
            update_vals['city'] = record_data['city']
        
        # Add other fields as needed...
        
        if update_vals:
            partner.write(update_vals)
        
        return partner

    def _create_subscription(self, partner, record_data):
        """Create subscription for partner"""
        if not self.default_membership_type_id:
            return None
        
        # Check if partner already has active subscription
        existing_subscription = self.env['ams.member.subscription'].search([
            ('partner_id', '=', partner.id),
            ('state', 'in', ['active', 'pending_renewal'])
        ], limit=1)
        
        if existing_subscription:
            return None
        
        subscription_vals = {
            'partner_id': partner.id,
            'membership_type_id': self.default_membership_type_id.id,
            'chapter_id': self.default_chapter_id.id if self.default_chapter_id else False,
            'start_date': self.default_start_date,
            'unit_price': self.default_membership_type_id.price,
        }
        
        # Override with imported data if available
        if record_data.get('start_date'):
            try:
                subscription_vals['start_date'] = fields.Date.from_string(record_data['start_date'])
            except:
                pass
        
        subscription = self.env['ams.member.subscription'].create(subscription_vals)
        
        # Auto-approve if requested
        if self.auto_approve_subscriptions:
            subscription.action_approve()
        
        return subscription

    def _send_welcome_email(self, partner):
        """Send welcome email to partner"""
        try:
            self.welcome_template_id.send_mail(partner.id, force_send=True)
        except Exception as e:
            _logger.warning(f"Failed to send welcome email to {partner.name}: {e}")

    def _format_import_results(self, results):
        """Format import results for display"""
        html = f"<div class='alert alert-success'>"
        html += f"<h5>Import Results</h5>"
        html += f"<p>Records Created: <strong>{results['created']}</strong></p>"
        html += f"<p>Records Updated: <strong>{results['updated']}</strong></p>"
        html += f"<p>Records Skipped: <strong>{results['skipped']}</strong></p>"
        html += f"<p>Records Failed: <strong>{results['failed']}</strong></p>"
        html += f"</div>"
        
        if results['log']:
            html += f"<div class='mt-3'>"
            html += f"<h5>Import Log</h5>"
            html += f"<div style='max-height: 300px; overflow-y: auto;'>"
            html += f"<ul class='list-unstyled'>"
            for log_entry in results['log']:
                html += f"<li><small>{log_entry}</small></li>"
            html += f"</ul>"
            html += f"</div>"
            html += f"</div>"
        
        return html

    def action_download_template(self):
        """Download CSV template for import"""
        # Create template with standard fields
        template_data = [
            ['name', 'email', 'phone', 'street', 'city', 'zip', 'membership_type', 'chapter', 'start_date'],
            ['John Doe', 'john@example.com', '555-1234', '123 Main St', 'Anytown', '12345', 'Professional', 'Main Chapter', '2024-01-01'],
            ['Jane Smith', 'jane@example.com', '555-5678', '456 Oak Ave', 'Somewhere', '67890', 'Student', 'Local Chapter', '2024-01-01']
        ]
        
        output = io.StringIO()
        writer = csv.writer(output, delimiter=self.delimiter)
        writer.writerows(template_data)
        
        template_content = output.getvalue()
        output.close()
        
        # Create attachment
        attachment = self.env['ir.attachment'].create({
            'name': 'member_import_template.csv',
            'type': 'binary',
            'datas': base64.b64encode(template_content.encode('utf-8')),
            'store_fname': 'member_import_template.csv',
            'mimetype': 'text/csv',
        })
        
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'self',
        }

    def action_cancel(self):
        """Cancel the wizard"""
        return {'type': 'ir.actions.act_window_close'}


class MemberImportMapping(models.TransientModel):
    _name = 'ams.member.import.mapping'
    _description = 'Member Import Field Mapping'
    _order = 'sequence'

    wizard_id = fields.Many2one(
        'ams.member.import.wizard',
        string='Wizard',
        required=True,
        ondelete='cascade'
    )
    
    sequence = fields.Integer(
        string='Sequence',
        default=10
    )
    
    csv_field = fields.Char(
        string='CSV Field',
        required=True,
        help="Column name from the CSV file"
    )
    
    odoo_field = fields.Selection([
        ('name', 'Name'),
        ('first_name', 'First Name'),
        ('last_name', 'Last Name'),
        ('email', 'Email'),
        ('phone', 'Phone'),
        ('mobile', 'Mobile'),
        ('street', 'Street'),
        ('street2', 'Street 2'),
        ('city', 'City'),
        ('zip', 'ZIP Code'),
        ('state', 'State'),
        ('country', 'Country'),
        ('membership_number', 'Membership Number'),
        ('membership_type', 'Membership Type'),
        ('chapter', 'Chapter'),
        ('start_date', 'Start Date'),
        ('end_date', 'End Date'),
        ('external_id', 'External ID'),
        ('notes', 'Notes'),
    ], string='Odoo Field', help="Corresponding field in Odoo")
    
    is_required = fields.Boolean(
        string='Required',
        default=False,
        help="This field is required for import"
    )
    
    default_value = fields.Char(
        string='Default Value',
        help="Default value if CSV field is empty"
    )
    
    sample_data = fields.Char(
        string='Sample Data',
        help="Sample data from CSV file"
    )