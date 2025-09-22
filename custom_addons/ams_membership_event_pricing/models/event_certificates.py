from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from datetime import datetime, timedelta
import base64
import logging

_logger = logging.getLogger(__name__)


class EventCertificate(models.Model):
    _name = 'event.certificate'
    _description = 'Event Certificate'
    _order = 'issue_date desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    # Basic Information
    name = fields.Char(
        string='Certificate Number',
        required=True,
        default=lambda self: self.env['ir.sequence'].next_by_code('event.certificate') or 'New',
        help="Unique certificate number"
    )
    event_id = fields.Many2one(
        'event.event',
        string='Event',
        required=True,
        help="Event this certificate is for"
    )
    registration_id = fields.Many2one(
        'event.registration',
        string='Registration',
        required=True,
        help="Registration this certificate is issued for"
    )
    partner_id = fields.Many2one(
        'res.partner',
        string='Recipient',
        required=True,
        help="Person receiving the certificate"
    )
    
    # Certificate Details
    issue_date = fields.Date(
        string='Issue Date',
        default=fields.Date.today,
        required=True,
        tracking=True,
        help="Date certificate was issued"
    )
    completion_date = fields.Date(
        string='Completion Date',
        help="Date when event/course was completed"
    )
    valid_until = fields.Date(
        string='Valid Until',
        help="Certificate expiry date (if applicable)"
    )
    
    # Certificate Content
    certificate_title = fields.Char(
        string='Certificate Title',
        help="Title shown on certificate"
    )
    description = fields.Text(
        string='Description',
        help="Description of achievement or completion"
    )
    instructor_name = fields.Char(
        string='Instructor Name',
        help="Name of instructor or presenter"
    )
    
    # Status and Validation
    state = fields.Selection([
        ('draft', 'Draft'),
        ('issued', 'Issued'),
        ('revoked', 'Revoked')
    ], string='Status', default='draft', required=True, tracking=True)
    
    verification_code = fields.Char(
        string='Verification Code',
        help="Code for online certificate verification"
    )
    
    # File Management
    certificate_file = fields.Binary(
        string='Certificate File',
        help="Generated certificate file (PDF)"
    )
    certificate_filename = fields.Char(
        string='Filename',
        compute='_compute_certificate_filename'
    )
    
    # CEU/CPE Credits
    ceu_credits = fields.Float(
        string='CEU Credits',
        help="Continuing Education Units awarded"
    )
    cpe_credits = fields.Float(
        string='CPE Credits',
        help="Continuing Professional Education credits"
    )
    credit_category = fields.Selection([
        ('technical', 'Technical'),
        ('non_technical', 'Non-Technical'),
        ('ethics', 'Ethics'),
        ('general', 'General'),
        ('other', 'Other')
    ], string='Credit Category', help="Category of continuing education credits")
    
    # Compliance and Reporting
    compliance_year = fields.Integer(
        string='Compliance Year',
        help="Year these credits apply to for compliance"
    )
    accreditation_body = fields.Char(
        string='Accreditation Body',
        help="Organization that accredits this education"
    )
    program_number = fields.Char(
        string='Program Number',
        help="Official program number from accrediting body"
    )
    
    # Template and Generation
    template_id = fields.Many2one(
        'event.certificate.template',
        string='Certificate Template',
        help="Template used to generate certificate"
    )

    @api.depends('partner_id.name', 'event_id.name', 'name')
    def _compute_certificate_filename(self):
        for cert in self:
            if cert.partner_id and cert.event_id:
                filename = f"{cert.partner_id.name}_{cert.event_id.name}_{cert.name}.pdf"
                cert.certificate_filename = filename.replace(' ', '_').replace('/', '-')
            else:
                cert.certificate_filename = f"certificate_{cert.name}.pdf"

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('verification_code'):
                vals['verification_code'] = self._generate_verification_code()
        return super().create(vals_list)

    def _generate_verification_code(self):
        """Generate unique verification code"""
        import random
        import string
        length = 12
        characters = string.ascii_uppercase + string.digits
        return ''.join(random.choice(characters) for _ in range(length))

    @api.onchange('event_id')
    def _onchange_event_id(self):
        if self.event_id:
            # Auto-populate from event
            self.certificate_title = f"Certificate of Completion - {self.event_id.name}"
            self.completion_date = self.event_id.date_end or self.event_id.date_begin
            self.ceu_credits = self.event_id.ceu_credits
            self.cpe_credits = self.event_id.cpe_credits
            self.credit_category = self.event_id.credit_category
            self.accreditation_body = self.event_id.accreditation_body
            self.program_number = self.event_id.program_number
            self.template_id = self.event_id.default_certificate_template_id

    def action_generate_certificate(self):
        """Generate certificate PDF"""
        self.ensure_one()
        
        if not self.template_id:
            raise UserError(_("No certificate template selected."))
        
        # Generate PDF certificate
        certificate_data = self._generate_certificate_pdf()
        
        self.write({
            'certificate_file': certificate_data,
            'state': 'issued'
        })
        
        # Send certificate via email
        self._send_certificate_email()
        
        self.message_post(body=_("Certificate generated and issued."))

    def _generate_certificate_pdf(self):
        """Generate certificate PDF using template"""
        self.ensure_one()
        
        # This would integrate with a PDF generation library
        # For now, return placeholder
        
        # Create certificate context
        context = {
            'recipient_name': self.partner_id.name,
            'event_name': self.event_id.name,
            'completion_date': self.completion_date,
            'certificate_number': self.name,
            'verification_code': self.verification_code,
            'ceu_credits': self.ceu_credits,
            'cpe_credits': self.cpe_credits,
            'instructor_name': self.instructor_name or 'Event Staff',
            'issue_date': self.issue_date,
        }
        
        # Generate PDF (placeholder - would use reportlab or similar)
        pdf_content = self._render_certificate_template(context)
        
        return base64.b64encode(pdf_content)

    def _render_certificate_template(self, context):
        """Render certificate template to PDF"""
        # Placeholder implementation
        # In real implementation, this would use reportlab, weasyprint, or similar
        pdf_content = f"CERTIFICATE OF COMPLETION\n\n"
        pdf_content += f"This certifies that\n\n"
        pdf_content += f"{context['recipient_name']}\n\n"
        pdf_content += f"has successfully completed\n\n"
        pdf_content += f"{context['event_name']}\n\n"
        pdf_content += f"on {context['completion_date']}\n\n"
        pdf_content += f"Certificate #: {context['certificate_number']}\n"
        pdf_content += f"Verification Code: {context['verification_code']}\n"
        
        if context['ceu_credits']:
            pdf_content += f"CEU Credits: {context['ceu_credits']}\n"
        if context['cpe_credits']:
            pdf_content += f"CPE Credits: {context['cpe_credits']}\n"
        
        return pdf_content.encode('utf-8')

    def _send_certificate_email(self):
        """Send certificate via email"""
        template = self.env.ref('membership_event_pricing.email_template_certificate_issued', False)
        if template and self.partner_id.email:
            template.send_mail(self.id, force_send=True)

    def action_revoke_certificate(self):
        """Revoke certificate"""
        self.ensure_one()
        
        self.state = 'revoked'
        self.message_post(body=_("Certificate revoked."))

    def action_download_certificate(self):
        """Download certificate file"""
        self.ensure_one()
        
        if not self.certificate_file:
            raise UserError(_("No certificate file available. Generate certificate first."))
        
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/event.certificate/{self.id}/certificate_file/{self.certificate_filename}',
            'target': 'new',
        }

    @api.model
    def verify_certificate(self, verification_code):
        """Verify certificate by verification code"""
        certificate = self.search([
            ('verification_code', '=', verification_code),
            ('state', '=', 'issued')
        ], limit=1)
        
        if certificate:
            return {
                'valid': True,
                'recipient_name': certificate.partner_id.name,
                'event_name': certificate.event_id.name,
                'issue_date': certificate.issue_date,
                'completion_date': certificate.completion_date,
                'certificate_number': certificate.name,
                'ceu_credits': certificate.ceu_credits,
                'cpe_credits': certificate.cpe_credits,
            }
        else:
            return {'valid': False}


class EventCertificateTemplate(models.Model):
    _name = 'event.certificate.template'
    _description = 'Event Certificate Template'
    _order = 'name'

    name = fields.Char(
        string='Template Name',
        required=True,
        help="Name of the certificate template"
    )
    description = fields.Text(
        string='Description',
        help="Description of when to use this template"
    )
    
    # Template Design
    template_type = fields.Selection([
        ('standard', 'Standard Template'),
        ('custom', 'Custom Template'),
        ('html', 'HTML Template')
    ], string='Template Type', default='standard', required=True)
    
    template_file = fields.Binary(
        string='Template File',
        help="Template file (for custom templates)"
    )
    template_filename = fields.Char(
        string='Template Filename'
    )
    
    html_template = fields.Html(
        string='HTML Template',
        help="HTML template for certificate generation"
    )
    
    # Default Settings
    default_ceu_credits = fields.Float(
        string='Default CEU Credits',
        help="Default CEU credits for certificates using this template"
    )
    default_cpe_credits = fields.Float(
        string='Default CPE Credits',
        help="Default CPE credits for certificates using this template"
    )
    
    # Settings
    active = fields.Boolean(
        string='Active',
        default=True,
        help="Uncheck to disable this template"
    )
    
    # Usage Statistics
    certificate_count = fields.Integer(
        string='Certificates Issued',
        compute='_compute_usage_stats'
    )

    @api.depends()  # Will be computed on demand
    def _compute_usage_stats(self):
        for template in self:
            template.certificate_count = self.env['event.certificate'].search_count([
                ('template_id', '=', template.id)
            ])


class MemberCertificate(models.Model):
    _name = 'member.certificate'
    _description = 'Member Certificate Summary'
    _auto = False
    _rec_name = 'partner_id'

    partner_id = fields.Many2one('res.partner', string='Member')
    total_certificates = fields.Integer(string='Total Certificates')
    total_ceu_credits = fields.Float(string='Total CEU Credits')
    total_cpe_credits = fields.Float(string='Total CPE Credits')
    latest_certificate_date = fields.Date(string='Latest Certificate')
    current_year_ceu = fields.Float(string='Current Year CEU')
    current_year_cpe = fields.Float(string='Current Year CPE')

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW %s AS (
                SELECT
                    ROW_NUMBER() OVER (ORDER BY p.id) AS id,
                    p.id AS partner_id,
                    COUNT(ec.id) AS total_certificates,
                    COALESCE(SUM(ec.ceu_credits), 0) AS total_ceu_credits,
                    COALESCE(SUM(ec.cpe_credits), 0) AS total_cpe_credits,
                    MAX(ec.issue_date) AS latest_certificate_date,
                    COALESCE(SUM(CASE WHEN EXTRACT(YEAR FROM ec.issue_date) = EXTRACT(YEAR FROM CURRENT_DATE) 
                                      THEN ec.ceu_credits ELSE 0 END), 0) AS current_year_ceu,
                    COALESCE(SUM(CASE WHEN EXTRACT(YEAR FROM ec.issue_date) = EXTRACT(YEAR FROM CURRENT_DATE) 
                                      THEN ec.cpe_credits ELSE 0 END), 0) AS current_year_cpe
                FROM res_partner p
                LEFT JOIN event_certificate ec ON ec.partner_id = p.id AND ec.state = 'issued'
                WHERE p.is_member = TRUE
                GROUP BY p.id
            )
        """ % self._table)


# Enhanced Event model with certificate functionality
class Event(models.Model):
    _inherit = 'event.event'

    # Certificate Settings
    issue_certificates = fields.Boolean(
        string='Issue Certificates',
        default=False,
        help="Issue certificates to attendees upon completion"
    )
    auto_issue_certificates = fields.Boolean(
        string='Auto-issue Certificates',
        default=False,
        help="Automatically issue certificates when event ends"
    )
    default_certificate_template_id = fields.Many2one(
        'event.certificate.template',
        string='Default Certificate Template',
        help="Default template for certificates"
    )
    
    # CEU/CPE Settings
    ceu_credits = fields.Float(
        string='CEU Credits',
        help="Continuing Education Units awarded for this event"
    )
    cpe_credits = fields.Float(
        string='CPE Credits',
        help="Continuing Professional Education credits"
    )
    credit_category = fields.Selection([
        ('technical', 'Technical'),
        ('non_technical', 'Non-Technical'),
        ('ethics', 'Ethics'),
        ('general', 'General'),
        ('other', 'Other')
    ], string='Credit Category')
    
    # Accreditation Information
    accreditation_body = fields.Char(
        string='Accreditation Body',
        help="Organization providing accreditation"
    )
    program_number = fields.Char(
        string='Program Number',
        help="Official program number"
    )
    
    # Certificate Statistics
    certificate_ids = fields.One2many(
        'event.certificate',
        'event_id',
        string='Certificates'
    )
    certificate_count = fields.Integer(
        string='Certificates Issued',
        compute='_compute_certificate_stats'
    )
    certificates_pending = fields.Integer(
        string='Certificates Pending',
        compute='_compute_certificate_stats'
    )

    @api.depends('certificate_ids.state')
    def _compute_certificate_stats(self):
        for event in self:
            certificates = event.certificate_ids
            event.certificate_count = len(certificates.filtered(lambda c: c.state == 'issued'))
            event.certificates_pending = len(certificates.filtered(lambda c: c.state == 'draft'))

    def action_view_certificates(self):
        """View event certificates"""
        self.ensure_one()
        return {
            'name': f"Certificates - {self.name}",
            'type': 'ir.actions.act_window',
            'res_model': 'event.certificate',
            'view_mode': 'tree,form',
            'domain': [('event_id', '=', self.id)],
            'context': {'default_event_id': self.id},
        }

    def action_generate_all_certificates(self):
        """Generate certificates for all attendees"""
        self.ensure_one()
        
        if not self.issue_certificates:
            raise UserError(_("Certificate issuance is not enabled for this event."))
        
        if not self.default_certificate_template_id:
            raise UserError(_("No default certificate template configured."))
        
        # Find attendees without certificates
        attendees = self.registration_ids.filtered(
            lambda r: r.state == 'done' and not r.certificate_id
        )
        
        certificates_created = 0
        for attendee in attendees:
            certificate = self.env['event.certificate'].create({
                'event_id': self.id,
                'registration_id': attendee.id,
                'partner_id': attendee.partner_id.id,
                'template_id': self.default_certificate_template_id.id,
            })
            
            certificate.action_generate_certificate()
            attendee.certificate_id = certificate.id
            certificates_created += 1
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': _('Generated %d certificates.') % certificates_created,
                'type': 'success',
            }
        }

    @api.model
    def auto_issue_certificates(self):
        """Cron job to auto-issue certificates for completed events"""
        yesterday = fields.Date.today() - timedelta(days=1)
        
        completed_events = self.search([
            ('date_end', '=', yesterday),
            ('issue_certificates', '=', True),
            ('auto_issue_certificates', '=', True),
            ('default_certificate_template_id', '!=', False)
        ])
        
        for event in completed_events:
            try:
                event.action_generate_all_certificates()
                _logger.info(f"Auto-issued certificates for event: {event.name}")
            except Exception as e:
                _logger.error(f"Failed to auto-issue certificates for event {event.name}: {str(e)}")


# Enhanced Registration model with certificate integration
class EventRegistration(models.Model):
    _inherit = 'event.registration'

    # Certificate Information
    certificate_id = fields.Many2one(
        'event.certificate',
        string='Certificate',
        help="Certificate issued for this registration"
    )
    has_certificate = fields.Boolean(
        string='Has Certificate',
        compute='_compute_has_certificate'
    )

    @api.depends('certificate_id')
    def _compute_has_certificate(self):
        for registration in self:
            registration.has_certificate = bool(registration.certificate_id)

    def action_issue_certificate(self):
        """Issue certificate for this registration"""
        self.ensure_one()
        
        if not self.event_id.issue_certificates:
            raise UserError(_("Certificate issuance is not enabled for this event."))
        
        if self.certificate_id:
            raise UserError(_("Certificate already exists for this registration."))
        
        if self.state != 'done':
            raise UserError(_("Certificate can only be issued for completed registrations."))
        
        certificate = self.env['event.certificate'].create({
            'event_id': self.event_id.id,
            'registration_id': self.id,
            'partner_id': self.partner_id.id,
            'template_id': self.event_id.default_certificate_template_id.id,
        })
        
        certificate.action_generate_certificate()
        self.certificate_id = certificate.id
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Event Certificate'),
            'res_model': 'event.certificate',
            'res_id': certificate.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_view_certificate(self):
        """View certificate for this registration"""
        self.ensure_one()
        
        if not self.certificate_id:
            raise UserError(_("No certificate exists for this registration."))
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Event Certificate'),
            'res_model': 'event.certificate',
            'res_id': self.certificate_id.id,
            'view_mode': 'form',
            'target': 'current',
        }


# Enhanced Partner model with certificate tracking
class ResPartner(models.Model):
    _inherit = 'res.partner'

    # Certificate Statistics
    certificate_ids = fields.One2many(
        'event.certificate',
        'partner_id',
        string='Certificates'
    )
    total_certificates = fields.Integer(
        string='Total Certificates',
        compute='_compute_certificate_stats'
    )
    total_ceu_credits = fields.Float(
        string='Total CEU Credits',
        compute='_compute_certificate_stats'
    )
    total_cpe_credits = fields.Float(
        string='Total CPE Credits',
        compute='_compute_certificate_stats'
    )
    current_year_ceu = fields.Float(
        string='Current Year CEU',
        compute='_compute_certificate_stats'
    )
    current_year_cpe = fields.Float(
        string='Current Year CPE',
        compute='_compute_certificate_stats'
    )

    @api.depends('certificate_ids.state', 'certificate_ids.ceu_credits', 'certificate_ids.cpe_credits')
    def _compute_certificate_stats(self):
        current_year = fields.Date.today().year
        
        for partner in self:
            issued_certs = partner.certificate_ids.filtered(lambda c: c.state == 'issued')
            partner.total_certificates = len(issued_certs)
            partner.total_ceu_credits = sum(issued_certs.mapped('ceu_credits'))
            partner.total_cpe_credits = sum(issued_certs.mapped('cpe_credits'))
            
            current_year_certs = issued_certs.filtered(
                lambda c: c.issue_date and c.issue_date.year == current_year
            )
            partner.current_year_ceu = sum(current_year_certs.mapped('ceu_credits'))
            partner.current_year_cpe = sum(current_year_certs.mapped('cpe_credits'))

    def action_view_certificates(self):
        """View all certificates for this partner"""
        self.ensure_one()
        return {
            'name': f"Certificates - {self.name}",
            'type': 'ir.actions.act_window',
            'res_model': 'event.certificate',
            'view_mode': 'tree,form',
            'domain': [('partner_id', '=', self.id)],
        }