# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
import json
import base64
import io
from datetime import datetime, timedelta
import logging

_logger = logging.getLogger(__name__)

# Optional reportlab imports for PDF generation
try:
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.lib import colors
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False
    _logger.warning("ReportLab not available - PDF export will be disabled")


class PrivacyExportWizard(models.TransientModel):
    _name = 'ams.privacy.export.wizard'
    _description = 'Privacy Data Export Wizard (GDPR Article 20)'

    # ===== PARTNER SELECTION =====
    partner_ids = fields.Many2many(
        'res.partner',
        string='Partners to Export',
        required=True,
        help="Select partners whose data should be exported"
    )

    single_partner_id = fields.Many2one(
        'res.partner',
        string='Partner',
        help="Single partner for export (when called from partner form)"
    )

    # ===== EXPORT OPTIONS =====
    export_format = fields.Selection([
        ('json', 'JSON (Machine Readable)'),
        ('pdf', 'PDF (Human Readable)'),
        ('both', 'Both JSON and PDF'),
    ], string='Export Format', required=True, default='json',
       help="Format for the exported data")

    include_profile_data = fields.Boolean(
        string='Include Profile Data',
        default=True,
        help="Include extended member profile information"
    )

    include_consent_history = fields.Boolean(
        string='Include Consent History',
        default=True,
        help="Include privacy consent records and history"
    )

    include_audit_trail = fields.Boolean(
        string='Include Audit Trail',
        default=False,
        help="Include audit log entries (may be very large)"
    )

    include_communications = fields.Boolean(
        string='Include Communications',
        default=False,
        help="Include email and message history"
    )

    include_relationships = fields.Boolean(
        string='Include Relationships',
        default=True,
        help="Include partner relationships (family, employer, etc.)"
    )

    include_attachments = fields.Boolean(
        string='Include Attachments',
        default=False,
        help="Include file attachments (photos, documents)"
    )

    # ===== DATE RANGE =====
    date_from = fields.Date(
        string='From Date',
        help="Only include data from this date onwards"
    )

    date_to = fields.Date(
        string='To Date',
        default=fields.Date.today,
        help="Only include data up to this date"
    )

    # ===== LEGAL BASIS =====
    export_reason = fields.Selection([
        ('gdpr_request', 'GDPR Data Subject Request'),
        ('ccpa_request', 'CCPA Consumer Request'),
        ('member_request', 'Member Data Request'),
        ('legal_compliance', 'Legal Compliance'),
        ('data_migration', 'Data Migration'),
        ('other', 'Other'),
    ], string='Export Reason', required=True, default='gdpr_request',
       help="Legal basis for this data export")

    export_justification = fields.Text(
        string='Justification',
        help="Detailed justification for this data export"
    )

    # ===== RECIPIENT INFORMATION =====
    recipient_name = fields.Char(
        string='Recipient Name',
        help="Name of the person/organization receiving the data"
    )

    recipient_email = fields.Char(
        string='Recipient Email',
        help="Email address of the recipient"
    )

    recipient_organization = fields.Char(
        string='Recipient Organization',
        help="Organization of the recipient"
    )

    # ===== OUTPUT =====
    export_file = fields.Binary(
        string='Export File',
        readonly=True,
        help="Generated export file"
    )

    export_filename = fields.Char(
        string='Filename',
        readonly=True,
        help="Name of the export file"
    )

    pdf_file = fields.Binary(
        string='PDF Export',
        readonly=True,
        help="PDF version of the export"
    )

    pdf_filename = fields.Char(
        string='PDF Filename',
        readonly=True,
        help="Name of the PDF export file"
    )

    # ===== STATUS =====
    state = fields.Selection([
        ('draft', 'Draft'),
        ('generating', 'Generating'),
        ('completed', 'Completed'),
        ('error', 'Error'),
    ], string='State', default='draft', readonly=True)

    error_message = fields.Text(
        string='Error Message',
        readonly=True,
        help="Error details if export failed"
    )

    # ===== STATISTICS =====
    records_exported = fields.Integer(
        string='Records Exported',
        readonly=True,
        help="Total number of records exported"
    )

    file_size = fields.Char(
        string='File Size',
        readonly=True,
        help="Size of the exported file"
    )

    export_duration = fields.Float(
        string='Export Duration (seconds)',
        readonly=True,
        help="Time taken to generate the export"
    )

    @api.onchange('single_partner_id')
    def _onchange_single_partner_id(self):
        """Set partner_ids when single_partner_id is set"""
        if self.single_partner_id:
            self.partner_ids = [(6, 0, [self.single_partner_id.id])]

    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        """Validate date range"""
        for wizard in self:
            if wizard.date_from and wizard.date_to:
                if wizard.date_from > wizard.date_to:
                    raise ValidationError(_("From date cannot be after To date"))

    @api.constrains('partner_ids')
    def _check_partner_limit(self):
        """Check partner export limit"""
        max_partners = int(self.env['ir.config_parameter'].sudo().get_param(
            'ams.privacy.max_export_partners', '10'
        ))
        
        for wizard in self:
            if len(wizard.partner_ids) > max_partners:
                raise ValidationError(
                    _("Cannot export data for more than %d partners at once") % max_partners
                )

    def action_generate_export(self):
        """Generate the data export"""
        self.ensure_one()
        
        if not self.partner_ids:
            raise UserError(_("Please select at least one partner to export"))
        
        # Check permissions
        if not self.env.user.has_group('ams_core_base.group_ams_privacy_officer'):
            raise UserError(_("Only privacy officers can export member data"))
        
        # Update state
        self.state = 'generating'
        
        try:
            start_time = datetime.now()
            
            # Generate export data
            export_data = self._generate_export_data()
            
            # Create files based on format
            if self.export_format in ['json', 'both']:
                self._create_json_export(export_data)
            
            if self.export_format in ['pdf', 'both']:
                if REPORTLAB_AVAILABLE:
                    self._create_pdf_export(export_data)
                else:
                    _logger.warning("PDF export requested but ReportLab not available")
            
            # Calculate statistics
            end_time = datetime.now()
            self.export_duration = (end_time - start_time).total_seconds()
            
            # Log the export
            self._log_export_activity()
            
            # Update partner export tracking
            self._update_partner_export_tracking()
            
            self.state = 'completed'
            
            return {
                'type': 'ir.actions.act_window',
                'res_model': self._name,
                'view_mode': 'form',
                'res_id': self.id,
                'target': 'new',
                'context': {'dialog_size': 'extra-large'},
            }
            
        except Exception as e:
            self.state = 'error'
            self.error_message = str(e)
            _logger.error(f"Privacy export failed: {e}")
            raise UserError(_("Export failed: %s") % str(e))

    def _generate_export_data(self):
        """Generate the export data structure"""
        export_data = {
            'export_metadata': {
                'generated_date': datetime.now().isoformat(),
                'generated_by': self.env.user.name,
                'export_reason': self.export_reason,
                'export_justification': self.export_justification,
                'date_range': {
                    'from': self.date_from.isoformat() if self.date_from else None,
                    'to': self.date_to.isoformat() if self.date_to else None,
                },
                'recipient': {
                    'name': self.recipient_name,
                    'email': self.recipient_email,
                    'organization': self.recipient_organization,
                },
                'data_categories_included': self._get_included_categories(),
            },
            'partners': []
        }
        
        record_count = 0
        
        # Fix: Properly iterate over partner recordset
        for partner in self.partner_ids:
            partner_data = self._export_partner_data(partner)
            export_data['partners'].append(partner_data)
            record_count += 1
        
        self.records_exported = record_count
        export_data['export_metadata']['total_partners'] = record_count
        
        return export_data

    def _export_partner_data(self, partner):
        """Export data for a single partner"""
        partner_data = {
            'basic_information': self._export_basic_partner_info(partner),
        }
        
        if self.include_profile_data and partner.member_profile_id:
            partner_data['profile_data'] = self._export_profile_data(partner)
        
        if self.include_consent_history:
            partner_data['consent_history'] = self._export_consent_data(partner)
        
        if self.include_relationships:
            partner_data['relationships'] = self._export_relationship_data(partner)
        
        if self.include_communications:
            partner_data['communications'] = self._export_communication_data(partner)
        
        if self.include_audit_trail:
            partner_data['audit_trail'] = self._export_audit_data(partner)
        
        if self.include_attachments:
            partner_data['attachments'] = self._export_attachment_data(partner)
        
        return partner_data

    def _export_basic_partner_info(self, partner):
        """Export basic partner information"""
        return {
            'id': partner.id,
            'name': partner.name,
            'preferred_name': partner.preferred_name,
            'email': partner.email,
            'phone': partner.phone,
            'mobile': partner.mobile,
            'website': partner.website,
            'is_company': partner.is_company,
            'is_member': partner.is_member,
            'member_id': partner.member_id,
            'member_status': partner.member_status,
            'member_since': partner.member_since.isoformat() if partner.member_since else None,
            'address': {
                'street': partner.street,
                'street2': partner.street2,
                'city': partner.city,
                'state': partner.state_id.name if partner.state_id else None,
                'zip': partner.zip,
                'country': partner.country_id.name if partner.country_id else None,
            },
            'professional_info': {
                'profession_discipline': partner.profession_discipline,
                'job_title_role': partner.job_title_role,
                'career_stage': partner.career_stage,
                'employer': partner.employer_id.name if partner.employer_id else None,
                'designations': [d.name for d in partner.professional_designation_ids],
                'specialties': [s.name for s in partner.specialty_ids],
            },
            'demographics': {
                'date_of_birth': partner.date_of_birth.isoformat() if partner.date_of_birth else None,
                'gender': partner.gender,
                'nationality': partner.nationality,
            },
            'dates': {
                'created': partner.create_date.isoformat(),
                'last_updated': partner.write_date.isoformat(),
            },
        }

    def _export_profile_data(self, partner):
        """Export member profile data"""
        if not partner.member_profile_id:
            return None
        
        profile = partner.member_profile_id[0]
        return {
            'education': {
                'graduation_year': profile.graduation_year,
                'graduation_institution': profile.graduation_institution,
            },
            'demographics': {
                'ethnicity': profile.ethnicity,
                'primary_language': profile.primary_language.name if profile.primary_language else None,
                'languages': [lang.name for lang in profile.language_ids],
                'time_zone': profile.time_zone,
                'geographic_region': profile.geographic_region,
            },
            'professional_networks': {
                'linkedin_url': profile.linkedin_url,
                'twitter_handle': profile.twitter_handle,
                'researchgate_url': profile.researchgate_url,
                'orcid_id': profile.orcid_id,
                'other_social_media': profile.other_social_media,
            },
            'engagement': {
                'volunteer_status': profile.volunteer_status,
                'volunteer_skills': profile.volunteer_skills,
                'interests': [tag.name for tag in profile.interests_tags],
                'engagement_score': profile.engagement_score,
                'total_events_attended': profile.total_events_attended,
                'continuing_education_hours': profile.continuing_education_hours,
            },
            'emergency_contact': {
                'name': profile.emergency_contact_name,
                'relationship': profile.emergency_contact_relationship,
                'phone': profile.emergency_contact_phone,
                'email': profile.emergency_contact_email,
            },
            'privacy_settings': {
                'photo_permission': profile.photo_permission,
                'marketing_consent': profile.marketing_consent,
                'directory_listing_consent': profile.directory_listing_consent,
                'data_sharing_consent': profile.data_sharing_consent,
            },
            'notes': {
                'member_notes': profile.member_notes,
                'internal_notes': profile.internal_notes,
            },
        }

    def _export_consent_data(self, partner):
        """Export consent history"""
        consents = partner.consent_ids
        if self.date_from:
            consents = consents.filtered(lambda c: c.consent_date.date() >= self.date_from)
        if self.date_to:
            consents = consents.filtered(lambda c: c.consent_date.date() <= self.date_to)
        
        consent_data = []
        for consent in consents:
            consent_data.append({
                'consent_type': consent.consent_type_id.name,
                'consent_category': consent.consent_type_id.category,
                'consent_given': consent.consent_given,
                'consent_date': consent.consent_date.isoformat(),
                'consent_method': consent.consent_method,
                'legal_basis': consent.legal_basis,
                'purpose': consent.purpose,
                'status': consent.status,
                'expiry_date': consent.expiry_date.isoformat() if consent.expiry_date else None,
                'withdrawal_date': consent.withdrawal_date.isoformat() if consent.withdrawal_date else None,
                'withdrawal_reason': consent.withdrawal_reason,
                'verified': consent.verified,
                'verification_date': consent.verification_date.isoformat() if consent.verification_date else None,
            })
        
        return consent_data

    def _export_relationship_data(self, partner):
        """Export relationship data"""
        # This method would be implemented when the relationships module is added
        # For now, return empty list
        return []

    def _export_communication_data(self, partner):
        """Export communication history"""
        messages = self.env['mail.message'].search([
            '|',
            ('partner_ids', 'in', partner.id),
            ('author_id', '=', partner.id),
        ])
        
        if self.date_from:
            messages = messages.filtered(lambda m: m.date.date() >= self.date_from)
        if self.date_to:
            messages = messages.filtered(lambda m: m.date.date() <= self.date_to)
        
        communications = []
        for message in messages:
            communications.append({
                'date': message.date.isoformat(),
                'message_type': message.message_type,
                'subject': message.subject,
                'body': message.body,
                'author': message.author_id.name if message.author_id else '',
                'recipients': [p.name for p in message.partner_ids],
                'email_from': message.email_from,
            })
        
        return communications

    def _export_audit_data(self, partner):
        """Export audit trail"""
        audit_logs = self.env['ams.audit.log'].search([
            ('related_partner_id', '=', partner.id)
        ])
        
        if self.date_from:
            date_from_dt = datetime.combine(self.date_from, datetime.min.time())
            audit_logs = audit_logs.filtered(lambda a: a.timestamp >= date_from_dt)
        if self.date_to:
            date_to_dt = datetime.combine(self.date_to, datetime.max.time())
            audit_logs = audit_logs.filtered(lambda a: a.timestamp <= date_to_dt)
        
        audit_data = []
        for log in audit_logs:
            audit_data.append({
                'timestamp': log.timestamp.isoformat(),
                'operation': log.operation,
                'model': log.model_name,
                'description': log.description,
                'user': log.user_id.name,
                'risk_level': log.risk_level,
                'is_sensitive': log.is_sensitive,
                'privacy_impact': log.privacy_impact,
            })
        
        return audit_data

    def _export_attachment_data(self, partner):
        """Export attachment information"""
        attachments = self.env['ir.attachment'].search([
            ('res_model', '=', 'res.partner'),
            ('res_id', '=', partner.id)
        ])
        
        attachment_data = []
        for attachment in attachments:
            attachment_info = {
                'name': attachment.name,
                'file_size': attachment.file_size,
                'mimetype': attachment.mimetype,
                'create_date': attachment.create_date.isoformat(),
                'description': attachment.description,
            }
            
            # Include file content if specifically requested and file is small
            if attachment.file_size < 1000000:  # 1MB limit
                attachment_info['file_content_base64'] = attachment.datas.decode() if attachment.datas else None
            
            attachment_data.append(attachment_info)
        
        return attachment_data

    def _get_included_categories(self):
        """Get list of included data categories"""
        categories = ['basic_information']
        
        if self.include_profile_data:
            categories.append('profile_data')
        if self.include_consent_history:
            categories.append('consent_history')
        if self.include_relationships:
            categories.append('relationships')
        if self.include_communications:
            categories.append('communications')
        if self.include_audit_trail:
            categories.append('audit_trail')
        if self.include_attachments:
            categories.append('attachments')
        
        return categories

    def _create_json_export(self, export_data):
        """Create JSON export file"""
        json_content = json.dumps(export_data, indent=2, ensure_ascii=False)
        json_bytes = json_content.encode('utf-8')
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        partner_names = '_'.join([p.name.replace(' ', '_') for p in self.partner_ids[:3]])
        if len(self.partner_ids) > 3:
            partner_names += f'_and_{len(self.partner_ids)-3}_more'
        
        filename = f"privacy_export_{partner_names}_{timestamp}.json"
        
        self.export_file = base64.b64encode(json_bytes)
        self.export_filename = filename
        self.file_size = f"{len(json_bytes) / 1024:.1f} KB"

    def _create_pdf_export(self, export_data):
        """Create PDF export file"""
        if not REPORTLAB_AVAILABLE:
            _logger.warning("Cannot create PDF export - ReportLab not available")
            return
        
        try:
            # Generate PDF using report
            pdf_content = self._generate_pdf_report(export_data)
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            partner_names = '_'.join([p.name.replace(' ', '_') for p in self.partner_ids[:3]])
            if len(self.partner_ids) > 3:
                partner_names += f'_and_{len(self.partner_ids)-3}_more'
            
            filename = f"privacy_export_{partner_names}_{timestamp}.pdf"
            
            self.pdf_file = base64.b64encode(pdf_content)
            self.pdf_filename = filename
            
        except Exception as e:
            _logger.warning(f"Failed to generate PDF export: {e}")
            # Continue without PDF if generation fails

    def _generate_pdf_report(self, export_data):
        """Generate PDF report content"""
        if not REPORTLAB_AVAILABLE:
            raise UserError(_("PDF generation not available - ReportLab library not installed"))
        
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        styles = getSampleStyleSheet()
        story = []
        
        # Title
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            spaceAfter=30,
            alignment=1,  # Center
        )
        
        story.append(Paragraph("Privacy Data Export Report", title_style))
        story.append(Spacer(1, 20))
        
        # Export metadata
        metadata = export_data['export_metadata']
        story.append(Paragraph("Export Information", styles['Heading2']))
        
        metadata_data = [
            ['Generated Date:', metadata['generated_date']],
            ['Generated By:', metadata['generated_by']],
            ['Export Reason:', metadata['export_reason']],
            ['Total Partners:', str(metadata['total_partners'])],
        ]
        
        metadata_table = Table(metadata_data, colWidths=[2*inch, 4*inch])
        metadata_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ]))
        
        story.append(metadata_table)
        story.append(Spacer(1, 20))
        
        # Partner data
        for partner_data in export_data['partners']:
            story.append(Paragraph(f"Partner: {partner_data['basic_information']['name']}", styles['Heading2']))
            
            # Basic information
            basic_info = partner_data['basic_information']
            story.append(Paragraph("Basic Information", styles['Heading3']))
            
            basic_data = [
                ['Name:', basic_info.get('name', '')],
                ['Email:', basic_info.get('email', '')],
                ['Phone:', basic_info.get('phone', '')],
                ['Member ID:', basic_info.get('member_id', '')],
                ['Member Status:', basic_info.get('member_status', '')],
            ]
            
            basic_table = Table(basic_data, colWidths=[2*inch, 4*inch])
            basic_table.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ]))
            
            story.append(basic_table)
            story.append(Spacer(1, 15))
            
            # Add other sections based on what was included
            if 'consent_history' in partner_data:
                story.append(Paragraph("Consent History", styles['Heading3']))
                consent_summary = f"Total consent records: {len(partner_data['consent_history'])}"
                story.append(Paragraph(consent_summary, styles['Normal']))
                story.append(Spacer(1, 10))
            
            if 'relationships' in partner_data:
                story.append(Paragraph("Relationships", styles['Heading3']))
                relationship_summary = f"Total relationships: {len(partner_data['relationships'])}"
                story.append(Paragraph(relationship_summary, styles['Normal']))
                story.append(Spacer(1, 10))
            
            story.append(Spacer(1, 20))
        
        # Build PDF
        doc.build(story)
        pdf_content = buffer.getvalue()
        buffer.close()
        
        return pdf_content

    def _log_export_activity(self):
        """Log the export activity in audit trail"""
        for partner in self.partner_ids:
            self.env['ams.audit.log'].create({
                'model_name': 'res.partner',
                'record_id': partner.id,
                'operation': 'export',
                'description': f'Privacy data export - {self.export_reason}',
                'user_id': self.env.user.id,
                'data': str({
                    'export_format': self.export_format,
                    'export_reason': self.export_reason,
                    'recipient': self.recipient_name,
                    'categories_included': self._get_included_categories(),
                    'records_exported': self.records_exported,
                }),
                'related_partner_id': partner.id,
                'privacy_impact': True,
                'risk_level': 'medium',
            })

    def _update_partner_export_tracking(self):
        """Update partner export tracking fields"""
        export_time = fields.Datetime.now()
        
        for partner in self.partner_ids:
            current_count = partner.data_export_count or 0
            partner.write({
                'last_data_export': export_time,
                'data_export_count': current_count + 1,
            })

    def action_download_json(self):
        """Download JSON export file"""
        self.ensure_one()
        
        if not self.export_file:
            raise UserError(_("No JSON export file available"))
        
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/ams.privacy.export.wizard/{self.id}/export_file/{self.export_filename}',
            'target': 'self',
        }

    def action_download_pdf(self):
        """Download PDF export file"""
        self.ensure_one()
        
        if not self.pdf_file:
            raise UserError(_("No PDF export file available"))
        
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/ams.privacy.export.wizard/{self.id}/pdf_file/{self.pdf_filename}',
            'target': 'self',
        }

    def action_email_export(self):
        """Email the export files"""
        self.ensure_one()
        
        if not self.recipient_email:
            raise UserError(_("Please specify recipient email address"))
        
        # Create email with attachments
        mail_values = {
            'subject': f'Privacy Data Export - {datetime.now().strftime("%Y-%m-%d")}',
            'body_html': self._get_email_body(),
            'email_to': self.recipient_email,
            'attachments': [],
        }
        
        if self.export_file:
            mail_values['attachments'].append((
                self.export_filename,
                base64.b64decode(self.export_file)
            ))
        
        if self.pdf_file:
            mail_values['attachments'].append((
                self.pdf_filename,
                base64.b64decode(self.pdf_file)
            ))
        
        # Send email
        mail = self.env['mail.mail'].create(mail_values)
        mail.send()
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': _('Export files emailed to %s') % self.recipient_email,
                'type': 'success',
            }
        }

    def _get_email_body(self):
        """Generate email body for export"""
        return f"""
        <p>Dear {self.recipient_name or 'Recipient'},</p>
        
        <p>Please find attached the requested privacy data export.</p>
        
        <p><strong>Export Details:</strong></p>
        <ul>
            <li>Export Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}</li>
            <li>Export Reason: {self.export_reason}</li>
            <li>Partners Included: {len(self.partner_ids)}</li>
            <li>Records Exported: {self.records_exported}</li>
            <li>Export Format: {self.export_format}</li>
        </ul>
        
        <p><strong>Data Categories Included:</strong></p>
        <ul>
            {''.join([f'<li>{category.replace("_", " ").title()}</li>' for category in self._get_included_categories()])}
        </ul>
        
        <p>This export was generated in response to your data portability request under applicable privacy regulations.</p>
        
        <p>If you have any questions about this export, please contact our privacy officer.</p>
        
        <p>Best regards,<br/>
        {self.env.user.name}<br/>
        Privacy Officer</p>
        """

    @api.model
    def cleanup_old_exports(self, days=30):
        """Clean up old export wizard records"""
        cutoff_date = fields.Datetime.now() - timedelta(days=days)
        old_exports = self.search([
            ('create_date', '<', cutoff_date),
            ('state', 'in', ['completed', 'error'])
        ])
        
        count = len(old_exports)
        if old_exports:
            old_exports.unlink()
            _logger.info(f"Cleaned up {count} old privacy export records")
        
        return count


class PrivacyConsentGrantWizard(models.TransientModel):
    _name = 'ams.privacy.consent.grant.wizard'
    _description = 'Grant Privacy Consent Wizard'

    # ===== PARTNER SELECTION =====
    partner_id = fields.Many2one(
        'res.partner',
        string='Partner',
        required=True,
        help="Partner to grant consent for"
    )

    partner_ids = fields.Many2many(
        'res.partner',
        string='Partners',
        help="Multiple partners for bulk consent granting"
    )

    # ===== CONSENT SELECTION =====
    consent_type_ids = fields.Many2many(
        'ams.privacy.consent.type',
        string='Consent Types',
        required=True,
        help="Types of consent to grant"
    )

    # ===== CONSENT DETAILS =====
    consent_method = fields.Selection([
        ('website', 'Website Form'),
        ('email', 'Email Response'),
        ('phone', 'Phone Call'),
        ('mail', 'Physical Mail'),
        ('in_person', 'In Person'),
        ('admin', 'Administrative'),
    ], string='Consent Method', required=True, default='admin')

    legal_basis = fields.Selection([
        ('consent', 'Consent'),
        ('contract', 'Contract'),
        ('legal_obligation', 'Legal Obligation'),
        ('vital_interests', 'Vital Interests'),
        ('public_task', 'Public Task'),
        ('legitimate_interests', 'Legitimate Interests'),
    ], string='Legal Basis', required=True, default='consent')

    purpose = fields.Text(
        string='Purpose',
        help="Specific purpose for which consent is granted"
    )

    expiry_date = fields.Date(
        string='Expiry Date',
        help="When this consent expires (optional)"
    )

    # ===== VERIFICATION =====
    ip_address = fields.Char(
        string='IP Address',
        help="IP address when consent was given"
    )

    user_agent = fields.Text(
        string='User Agent',
        help="Browser/device information"
    )

    notes = fields.Text(
        string='Notes',
        help="Additional notes about consent granting"
    )

    def action_grant_consent(self):
        """Grant the selected consents"""
        partners = self.partner_ids if self.partner_ids else self.partner_id
        
        if not partners:
            raise UserError(_("Please select at least one partner"))
        
        created_consents = []
        
        for partner in partners:
            for consent_type in self.consent_type_ids:
                # Check if active consent already exists
                existing_consent = self.env['ams.privacy.consent'].search([
                    ('partner_id', '=', partner.id),
                    ('consent_type_id', '=', consent_type.id),
                    ('status', '=', 'active'),
                ], limit=1)
                
                if existing_consent:
                    continue  # Skip if already has active consent
                
                # Create new consent record
                consent_vals = {
                    'partner_id': partner.id,
                    'consent_type_id': consent_type.id,
                    'consent_given': True,
                    'consent_method': self.consent_method,
                    'legal_basis': self.legal_basis,
                    'purpose': self.purpose,
                    'expiry_date': self.expiry_date,
                    'ip_address': self.ip_address,
                    'user_agent': self.user_agent,
                    'notes': self.notes,
                }
                
                # Set expiry based on consent type defaults if not specified
                if not self.expiry_date and consent_type.has_expiry:
                    if consent_type.default_expiry_days:
                        consent_vals['expiry_date'] = fields.Date.today() + timedelta(
                            days=consent_type.default_expiry_days
                        )
                
                consent = self.env['ams.privacy.consent'].create(consent_vals)
                created_consents.append(consent)
        
        if created_consents:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': _('Successfully granted %d consent(s)') % len(created_consents),
                    'type': 'success',
                }
            }
        else:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': _('No new consents were granted (may already exist)'),
                    'type': 'warning',
                }
            }


class PrivacyConsentWithdrawWizard(models.TransientModel):
    _name = 'ams.privacy.consent.withdraw.wizard'
    _description = 'Withdraw Privacy Consent Wizard'

    # ===== PARTNER SELECTION =====
    partner_ids = fields.Many2many(
        'res.partner',
        string='Partners',
        required=True,
        help="Partners to withdraw consent for"
    )

    consent_id = fields.Many2one(
        'ams.privacy.consent',
        string='Specific Consent',
        help="Specific consent record to withdraw"
    )

    # ===== CONSENT SELECTION =====
    consent_type_ids = fields.Many2many(
        'ams.privacy.consent.type',
        string='Consent Types to Withdraw',
        help="Types of consent to withdraw"
    )

    withdraw_all = fields.Boolean(
        string='Withdraw All Consents',
        default=False,
        help="Withdraw all active consents for selected partners"
    )

    # ===== WITHDRAWAL DETAILS =====
    withdrawal_reason = fields.Text(
        string='Withdrawal Reason',
        required=True,
        help="Reason for withdrawing consent"
    )

    withdrawal_method = fields.Selection([
        ('website', 'Website'),
        ('email', 'Email'),
        ('phone', 'Phone'),
        ('mail', 'Mail'),
        ('in_person', 'In Person'),
        ('admin', 'Administrative'),
    ], string='Withdrawal Method', required=True, default='admin')

    notify_partner = fields.Boolean(
        string='Notify Partner',
        default=True,
        help="Send confirmation email to partner"
    )

    def action_withdraw_consent(self):
        """Withdraw the selected consents"""
        if self.consent_id:
            # Withdraw specific consent
            consents_to_withdraw = [self.consent_id]
        else:
            # Find consents to withdraw
            consents_to_withdraw = []
            
            for partner in self.partner_ids:
                if self.withdraw_all:
                    # Withdraw all active consents
                    partner_consents = partner.consent_ids.filtered(lambda c: c.status == 'active')
                else:
                    # Withdraw specific types
                    partner_consents = partner.consent_ids.filtered(
                        lambda c: c.status == 'active' and c.consent_type_id in self.consent_type_ids
                    )
                
                consents_to_withdraw.extend(partner_consents)
        
        if not consents_to_withdraw:
            raise UserError(_("No active consents found to withdraw"))
        
        # Withdraw consents
        withdrawn_count = 0
        for consent in consents_to_withdraw:
            if consent.can_withdraw:
                consent.write({
                    'consent_given': False,
                    'withdrawal_date': fields.Datetime.now(),
                    'withdrawal_reason': self.withdrawal_reason,
                    'withdrawal_method': self.withdrawal_method,
                })
                withdrawn_count += 1
        
        # Send notifications if requested
        if self.notify_partner and withdrawn_count > 0:
            self._send_withdrawal_notifications(consents_to_withdraw)
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': _('Successfully withdrew %d consent(s)') % withdrawn_count,
                'type': 'success',
            }
        }

    def _send_withdrawal_notifications(self, withdrawn_consents):
        """Send withdrawal confirmation emails"""
        # Group by partner
        partners_consents = {}
        for consent in withdrawn_consents:
            partner = consent.partner_id
            if partner not in partners_consents:
                partners_consents[partner] = []
            partners_consents[partner].append(consent)
        
        # Send email to each partner
        for partner, consents in partners_consents.items():
            if partner.email:
                self._send_withdrawal_email(partner, consents)

    def _send_withdrawal_email(self, partner, consents):
        """Send withdrawal confirmation email to partner"""
        consent_list = '\n'.join([f"- {c.consent_type_id.name}" for c in consents])
        
        body = f"""
        <p>Dear {partner.name},</p>
        
        <p>This confirms that your consent has been withdrawn for the following:</p>
        
        <pre>{consent_list}</pre>
        
        <p>Withdrawal Date: {fields.Datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
        <p>Reason: {self.withdrawal_reason}</p>
        
        <p>We will stop processing your personal data for these purposes, 
        except where we have another legal basis to continue processing.</p>
        
        <p>If you have any questions, please contact our privacy officer.</p>
        
        <p>Best regards,<br/>Privacy Team</p>
        """
        
        mail_values = {
            'subject': 'Consent Withdrawal Confirmation',
            'body_html': body,
            'email_to': partner.email,
            'auto_delete': True,
        }
        
        mail = self.env['mail.mail'].create(mail_values)
        mail.send()


class PrivacyLegalHoldWizard(models.TransientModel):
    _name = 'ams.privacy.legal.hold.wizard'
    _description = 'Legal Hold Wizard'

    # ===== PARTNER SELECTION =====
    partner_id = fields.Many2one(
        'res.partner',
        string='Partner',
        required=True,
        help="Partner to place under legal hold"
    )

    # ===== LEGAL HOLD DETAILS =====
    legal_hold_reason = fields.Text(
        string='Legal Hold Reason',
        required=True,
        help="Detailed reason for placing legal hold"
    )

    case_reference = fields.Char(
        string='Case Reference',
        help="Legal case or investigation reference number"
    )

    hold_type = fields.Selection([
        ('litigation', 'Litigation Hold'),
        ('investigation', 'Investigation'),
        ('regulatory', 'Regulatory Inquiry'),
        ('audit', 'Audit'),
        ('other', 'Other'),
    ], string='Hold Type', required=True, default='litigation')

    requesting_party = fields.Char(
        string='Requesting Party',
        help="Who requested the legal hold (lawyer, court, etc.)"
    )

    expected_duration = fields.Char(
        string='Expected Duration',
        help="Expected duration of the legal hold"
    )

    # ===== SCOPE =====
    include_related_records = fields.Boolean(
        string='Include Related Records',
        default=True,
        help="Also hold related records (relationships, communications, etc.)"
    )

    hold_all_data = fields.Boolean(
        string='Hold All Data',
        default=True,
        help="Hold all data or only specific categories"
    )

    specific_data_categories = fields.Text(
        string='Specific Data Categories',
        help="Specific data categories to hold (if not holding all)"
    )

    def action_place_legal_hold(self):
        """Place legal hold on partner"""
        self.ensure_one()
        
        if not self.env.user.has_group('ams_core_base.group_ams_admin'):
            raise UserError(_("Only administrators can place legal holds"))
        
        # Update partner record
        self.partner_id.write({
            'legal_hold': True,
            'legal_hold_reason': self.legal_hold_reason,
            'legal_hold_date': fields.Date.today(),
        })
        
        # Log the legal hold
        self.env['ams.audit.log'].create({
            'model_name': 'res.partner',
            'record_id': self.partner_id.id,
            'operation': 'other',
            'description': f'Legal hold placed: {self.hold_type}',
            'user_id': self.env.user.id,
            'data': str({
                'hold_type': self.hold_type,
                'case_reference': self.case_reference,
                'requesting_party': self.requesting_party,
                'reason': self.legal_hold_reason,
                'include_related': self.include_related_records,
            }),
            'related_partner_id': self.partner_id.id,
            'privacy_impact': True,
            'risk_level': 'critical',
        })
        
        # Handle related records if requested
        if self.include_related_records:
            self._place_hold_on_related_records()
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': _('Legal hold successfully placed on %s') % self.partner_id.name,
                'type': 'success',
            }
        }

    def _place_hold_on_related_records(self):
        """Place holds on related records"""
        # This would extend to hold related records like
        # family members, business relationships, etc.
        # Implementation depends on specific requirements
        pass