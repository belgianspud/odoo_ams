# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime
import base64
import io
import csv
import logging

_logger = logging.getLogger(__name__)


class SubscriptionUsageImportWizard(models.TransientModel):
    _name = 'subscription.usage.import.wizard'
    _description = 'Import Usage Data'

    file_data = fields.Binary('Usage File', required=True)
    file_name = fields.Char('File Name')
    file_type = fields.Selection([
        ('csv', 'CSV'),
        ('excel', 'Excel'),
    ], string='File Type', required=True, default='csv')

    subscription_id = fields.Many2one('subscription.subscription', 'Subscription')
    usage_type = fields.Char('Usage Type', required=True)
    date_column = fields.Char('Date Column', default='date')
    quantity_column = fields.Char('Quantity Column', default='quantity')
    description_column = fields.Char('Description Column', default='description')

    def action_import_usage(self):
        """Import usage data from file"""
        if not self.file_data:
            raise UserError(_("Please upload a file"))

        # Decode file data
        file_content = base64.b64decode(self.file_data)
        
        if self.file_type == 'csv':
            return self._import_csv_usage(file_content)
        elif self.file_type == 'excel':
            return self._import_excel_usage(file_content)

    def _import_csv_usage(self, file_content):
        """Import usage from CSV"""
        csv_file = io.StringIO(file_content.decode('utf-8'))
        reader = csv.DictReader(csv_file)
        
        usage_records = []
        error_lines = []
        
        for line_num, row in enumerate(reader, start=2):
            try:
                usage_data = self._process_usage_row(row)
                usage_records.append(usage_data)
            except Exception as e:
                error_lines.append(f"Line {line_num}: {str(e)}")
        
        # Create usage records
        created_count = 0
        for usage_data in usage_records:
            try:
                self.env['subscription.usage'].create(usage_data)
                created_count += 1
            except Exception as e:
                error_lines.append(f"Error creating usage: {str(e)}")
        
        # Show result
        message = f"Successfully imported {created_count} usage records"
        if error_lines:
            message += f"\n\nErrors:\n" + "\n".join(error_lines[:10])
            if len(error_lines) > 10:
                message += f"\n... and {len(error_lines) - 10} more errors"
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Import Completed'),
                'message': message,
                'type': 'success' if not error_lines else 'warning',
                'sticky': True,
            }
        }

    def _import_excel_usage(self, file_content):
        """Import usage from Excel"""
        # This would require openpyxl or similar library
        # For now, just raise not implemented
        raise UserError(_("Excel import not implemented yet. Please use CSV format."))

    def _process_usage_row(self, row):
        """Process a single usage row"""
        # Parse date
        date_str = row.get(self.date_column, '')
        if not date_str:
            raise ValidationError(f"Missing date in column '{self.date_column}'")
        
        try:
            usage_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            try:
                usage_date = datetime.strptime(date_str, '%m/%d/%Y').date()
            except ValueError:
                raise ValidationError(f"Invalid date format: {date_str}")
        
        # Parse quantity
        quantity_str = row.get(self.quantity_column, '0')
        try:
            quantity = float(quantity_str)
        except ValueError:
            raise ValidationError(f"Invalid quantity: {quantity_str}")
        
        # Get description
        description = row.get(self.description_column, '')
        
        return {
            'subscription_id': self.subscription_id.id,
            'date': usage_date,
            'usage_type': self.usage_type,
            'quantity': quantity,
            'description': description,
            'billable': True,
        }