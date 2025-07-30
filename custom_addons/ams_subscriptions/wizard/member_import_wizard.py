from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from dateutil.relativedelta import relativedelta
import base64
import csv
import io
import logging

_logger = logging.getLogger(__name__)


class MemberImportWizard(models.TransientModel):
    _name = 'ams.member.import.wizard'
    _description = 'Member Import Wizard'

    # Import File
    import_file = fields.Binary(
        string='Import File',
        required=True,
        help="CSV file containing member data"
    )
    
    import_filename = fields.Char(
        string='Filename',
        help="Name of the imported file"
    )
    
    file_type = fields.Selection([
        ('csv', 'CSV File'),
        ('excel', 'Excel File')
    ], string='File Type', default='csv', required=True)

    # Import Options
    import_type = fields.Selection([
        ('members_only', 'Members Only'),
        ('members_and_subscriptions', 'Members and Subscriptions'),
        ('subscriptions_only', 'Subscriptions Only (existing members)')
    ], string='Import Type', default='members_and_subscriptions', required=True)
    
    update_existing = fields.Boolean(
        string='Update Existing Records',
        default=False,
        help="Update existing members if found by email or membership number"
    )
    
    create_missing_data = fields.Boolean(
        string='Create Missing Data',
        default=True,
        help="Automatically create missing membership types and chapters"
    )

    # CSV Settings
    has_header = fields.Boolean(
        string='File has Header Row',
        default=True,
        help="First row contains column headers"
    )
    
    delimiter = fields.Selection([
        (',', 'Comma (,)'),
        (';', 'Semicolon (;)'),
        ('\t', 'Tab'),
        ('|', 'Pipe (|)')
    ], string='Field Delimiter', default=',')
    
    encoding = fields.Selection([
        ('utf-8', 'UTF-8'),
        ('latin-1', 'Latin-1'),
        ('cp1252', 'Windows-1252')
    ], string='File Encoding', default='utf-8')

    # Default Values
    default_membership_type_id = fields.Many2one(
        'ams.membership.type',
        string='Default Membership Type',
        help="Default membership type for records without one specified"
    )
    
    default_chapter_id = fields.Many2one(
        'ams.chapter',
        string='Default Chapter',
        help="Default chapter for records without one specified"
    )
    
    default_start_date = fields.Date(
        string='Default Start Date',
        default=fields.Date.context_today,
        help="Default subscription start date"
    )
    
    default_payment_status = fields.Selection([
        ('paid', 'Paid'),
        ('unpaid', 'Unpaid'),
        ('partial', 'Partially Paid')
    ], string='Default Payment Status', default='unpaid')

    # Field Mapping
    field_mapping_ids = fields.One2many(
        'ams.member.import.field.mapping',
        'wizard_id',
        string='Field Mappings'
    )

    # Processing Options
    batch_size = fields.Integer(
        string='Batch Size',
        default=100,
        help="Number of records to process at once"
    )
    
    skip_validation_errors = fields.Boolean(
        string='Skip Validation Errors',
        default=False,
        help="Skip records with validation errors instead of stopping import"
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
    preview_data = fields.Html(
        string='Data Preview',
        compute='_compute_preview_data'
    )
    
    validation_results = fields.Html(
        string='Validation Results',
        compute='_compute_validation_results'
    )
    
    file_parsed = fields.Boolean(
        string='File Parsed',
        default=False
    )
    
    total_rows = fields.Integer(
        string='Total Rows',
        default=0
    )
    
    valid_rows = fields.Integer(
        string='Valid Rows',
        default=0
    )
    
    error_rows = fields.Integer(
        string='Error Rows',
        default=0
    )

    # Processing Results
    processing_log = fields.Html(
        string='Processing Log',
        readonly=True
    )
    
    members_created = fields.Integer(
        string='Members Created',
        readonly=True
    )
    
    members_updated = fields.Integer(
        string='Members Updated',
        readonly=True
    )
    
    subscriptions_created = fields.Integer(
        string='Subscriptions Created',
        readonly=True
    )
    
    errors_encountered = fields.Integer(
        string='Errors Encountered',
        readonly=True
    )
    
    import_completed = fields.Boolean(
        string='Import Completed',
        default=False,
        readonly=True
    )

    @api.onchange('import_file', 'import_filename')
    def _onchange_import_file(self):
        """Parse file when uploaded"""
        if self.import_file and self.import_filename:
            # Determine file type from extension
            if self.import_filename.lower().endswith('.csv'):
                self.file_type = 'csv'
            elif self.import_filename.lower().endswith(('.xlsx', '.xls')):
                self.file_type = 'excel'
            
            # Parse the file
            self._parse_file()

    def _parse_file(self):
        """Parse the uploaded file"""
        if not self.import_file:
            return
        
        try:
            # Decode file
            file_data = base64.b64decode(self.import_file)
            
            if self.file_type == 'csv':
                self._parse_csv_file(file_data)
            else:
                raise UserError(_("Excel import not yet implemented"))
            
            self.file_parsed = True
            
        except Exception as e:
            _logger.error(f"File parsing failed: {e}")
            raise UserError(_("Failed to parse file: %s") % str(e))

    def _parse_csv_file(self, file_data):
        """Parse CSV file"""
        try:
            # Decode with specified encoding
            content = file_data.decode(self.encoding)
            csv_file = io.StringIO(content)
            
            # Create CSV reader
            reader = csv.reader(csv_file, delimiter=self.delimiter)
            rows = list(reader)
            
            if not rows:
                raise UserError(_("File appears to be empty"))
            
            self.total_rows = len(rows)
            
            # Get headers
            if self.has_header:
                headers = rows[0]
                data_rows = rows[1:]
                self.total_rows -= 1
            else:
                headers = [f"Column_{i+1}" for i in range(len(rows[0]))]
                data_rows = rows
            
            # Create or update field mappings
            self._create_field_mappings(headers)
            
            # Store parsed data for preview
            self._store_parsed_data(headers, data_rows[:10])  # Store first 10 rows for preview
            
        except UnicodeDecodeError:
            raise UserError(_("Failed to decode file. Please check the encoding setting."))
        except Exception as e:
            raise UserError(_("Failed to parse CSV file: %s") % str(e))

    def _create_field_mappings(self, headers):
        """Create field mappings based on CSV headers"""
        # Clear existing mappings
        self.field_mapping_ids.unlink()
        
        # Common field mappings
        field_mapping_suggestions = {
            'name': ['name', 'full_name', 'member_name', 'first_name', 'fname'],
            'email': ['email', 'email_address', 'e_mail'],
            'phone': ['phone', 'telephone', 'mobile', 'cell'],
            'street': ['address', 'street', 'address1', 'street_address'],
            'city': ['city', 'town'],
            'zip': ['zip', 'postal_code', 'postcode'],
            'membership_number': ['membership_number', 'member_number', 'member_id'],
            'membership_type': ['membership_type', 'type', 'member_type'],
            'chapter': ['chapter', 'chapter_name', 'local_chapter'],
            'start_date': ['start_date', 'join_date', 'member_since'],
            'end_date': ['end_date', 'expiry_date', 'expires'],
        }
        
        mappings = []
        for i, header in enumerate(headers):
            header_lower = header.lower().strip()
            
            # Find best match
            target_field = None
            for field, suggestions in field_mapping_suggestions.items():
                if any(suggestion in header_lower for suggestion in suggestions):
                    target_field = field
                    break
            
            mappings.append({
                'sequence': i + 1,
                'csv_field': header,
                'target_field': target_field,
                'required': target_field in ['name', 'email'],
                'sample_data': ''  # Will be filled during validation
            })
        
        # Create mapping records
        for mapping in mappings:
            self.env['ams.member.import.field.mapping'].create({
                'wizard_id': self.id,
                **mapping
            })

    def _store_parsed_data(self, headers, data_rows):
        """Store parsed data for preview"""
        # This would store the parsed data in a temporary model or cache
        # For now, we'll just mark as parsed
        pass

    @api.depends('field_mapping_ids', 'file_parsed')
    def _compute_preview_data(self):
        """Compute preview data"""
        for wizard in self:
            if not wizard.file_parsed or not wizard.field_mapping_ids:
                wizard.preview_data = "<p>Please upload and parse a file first.</p>"