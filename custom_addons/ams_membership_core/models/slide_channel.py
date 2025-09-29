# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
import logging

_logger = logging.getLogger(__name__)


class SlideChannel(models.Model):
    _inherit = 'slide.channel'

    # AMS Integration
    is_ams_course = fields.Boolean('AMS Managed Course', default=False,
                                  help="Enable AMS membership features for this course")
    
    # Course Classification
    course_category = fields.Selection([
        ('technical', 'Technical Skills'),
        ('leadership', 'Leadership Development'),
        ('compliance', 'Compliance Training'),
        ('professional_development', 'Professional Development'),
        ('certification_prep', 'Certification Preparation'),
        ('industry_trends', 'Industry Trends'),
        ('software_training', 'Software Training'),
        ('safety', 'Safety Training'),
        ('ethics', 'Ethics and Standards'),
        ('business_skills', 'Business Skills')
    ], string='Course Category', help="Category for AMS course classification")
    
    course_level = fields.Selection([
        ('beginner', 'Beginner'),
        ('intermediate', 'Intermediate'),
        ('advanced', 'Advanced'),
        ('expert', 'Expert'),
        ('all_levels', 'All Levels')
    ], string='Course Level', default='intermediate')
    
    difficulty_level = fields.Selection([
        ('easy', 'Easy'),
        ('medium', 'Medium'),
        ('hard', 'Hard')
    ], string='Difficulty Level', default='medium')
    
    # Continuing Education Credits
    ce_credits = fields.Float('CE Credits Available', default=0.0,
                             help="Continuing education credits awarded upon completion")
    ce_provider = fields.Char('CE Provider', help="Organization providing CE credit approval")
    ce_approval_number = fields.Char('CE Approval Number', help="Official approval number for CE credits")
    ce_requirements = fields.Text('CE Requirements', help="Requirements to earn CE credits")
    
    # Pricing and Access
    member_price = fields.Float('Member Price', default=0.0,
                               help="Special pricing for association members")
    non_member_price = fields.Float('Non-Member Price', compute='_compute_non_member_price', store=True)
    requires_membership = fields.Boolean('Requires Membership', default=False,
                                       help="Only association members can enroll")
    guest_purchase_allowed = fields.Boolean('Guest Purchase Allowed', default=True,
                                          help="Non-members can purchase this course")
    
    # Course Duration and Access
    estimated_duration_hours = fields.Float('Estimated Duration (Hours)', default=0.0,
                                          help="Estimated time to complete the course")
    access_duration_days = fields.Integer('Access Duration (Days)', default=365,
                                        help="Days of access after enrollment")
    
    # Instructor Information
    instructor_bio = fields.Html('Instructor Bio')
    instructor_credentials = fields.Text('Instructor Credentials')
    
    # Prerequisites and Requirements
    prerequisites = fields.Html('Prerequisites', help="Course prerequisites and requirements")
    learning_objectives = fields.Html('Learning Objectives', help="What students will learn")
    target_audience = fields.Text('Target Audience', help="Who should take this course")
    
    # Assessment and Certification
    passing_score = fields.Float('Passing Score (%)', default=70.0,
                                help="Minimum score required to pass assessments")
    max_attempts = fields.Integer('Maximum Attempts', default=3,
                                help="Maximum attempts for quizzes and assessments")
    certificate_template_id = fields.Many2one('slide.channel.certificate', 'Certificate Template')
    
    # AMS Statistics
    member_enrollments = fields.Integer('Member Enrollments', compute='_compute_enrollment_stats')
    non_member_enrollments = fields.Integer('Non-Member Enrollments', compute='_compute_enrollment_stats')
    total_ce_credits_issued = fields.Float('Total CE Credits Issued', compute='_compute_ce_stats')
    completion_rate = fields.Float('Completion Rate (%)', compute='_compute_completion_stats')
    
    # Integration with Products
    product_template_ids = fields.One2many('product.template', 'course_id', 'Related Products')
    is_purchasable = fields.Boolean('Purchasable Course', compute='_compute_is_purchasable')

    @api.depends('list_price', 'member_price')
    def _compute_non_member_price(self):
        """Set non-member price to list price if member price is set"""
        for course in self:
            if course.member_price > 0:
                course.non_member_price = course.list_price
            else:
                course.non_member_price = 0.0

    def _compute_enrollment_stats(self):
        """Compute enrollment statistics"""
        for course in self:
            enrollments = course.channel_partner_ids
            member_enrollments = enrollments.filtered(lambda e: e.partner_id.is_member)
            
            course.member_enrollments = len(member_enrollments)
            course.non_member_enrollments = len(enrollments) - len(member_enrollments)

    def _compute_ce_stats(self):
        """Compute CE credit statistics"""
        for course in self:
            completed_enrollments = course.channel_partner_ids.filtered('completed')
            course.total_ce_credits_issued = len(completed_enrollments) * course.ce_credits

    def _compute_completion_stats(self):
        """Compute completion statistics"""
        for course in self:
            total_enrollments = len(course.channel_partner_ids)
            completed_enrollments = len(course.channel_partner_ids.filtered('completed'))
            
            if total_enrollments > 0:
                course.completion_rate = (completed_enrollments / total_enrollments) * 100
            else:
                course.completion_rate = 0.0

    def _compute_is_purchasable(self):
        """Check if course has associated products"""
        for course in self:
            course.is_purchasable = len(course.product_template_ids) > 0

    # Action Methods
    def action_create_product(self):
        """Create a product for this course"""
        self.ensure_one()
        
        if not self.is_ams_course:
            raise UserError(_("Course must be marked as AMS managed to create products."))
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Create Course Product'),
            'res_model': 'ams.course.product.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_course_id': self.id,
                'default_name': self.name,
                'default_list_price': self.non_member_price or 0.0,
            }
        }

    def action_view_products(self):
        """View related products"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Course Products'),
            'res_model': 'product.template',
            'view_mode': 'list,form',
            'domain': [('course_id', '=', self.id)],
        }

    def action_enrollment_report(self):
        """Generate enrollment report"""
        self.ensure_one()
        return {
            'type': 'ir.actions.report',
            'report_name': 'ams_membership_core.course_enrollment_report',
            'report_type': 'qweb-pdf',
            'data': {'course_id': self.id},
            'context': {'active_id': self.id},
        }

    def action_issue_certificates(self):
        """Issue certificates to completed students"""
        self.ensure_one()
        
        completed_partners = self.channel_partner_ids.filtered(
            lambda p: p.completed and not p.ams_certificate_issued
        )
        
        if not completed_partners:
            raise UserError(_("No completed students without certificates found."))
        
        for partner_progress in completed_partners:
            partner_progress.action_issue_ams_certificate()
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Certificates Issued'),
                'message': _('Certificates issued to %d students.') % len(completed_partners),
                'type': 'success'
            }
        }

    # Course Management Methods
    def get_member_price(self, partner):
        """Get appropriate price for partner"""
        self.ensure_one()
        
        if not partner:
            return self.non_member_price or self.list_price
        
        if partner.is_member and self.member_price > 0:
            return self.member_price
        else:
            return self.non_member_price or self.list_price

    def check_enrollment_eligibility(self, partner):
        """Check if partner can enroll in this course"""
        self.ensure_one()
        
        issues = []
        
        if self.requires_membership and (not partner or not partner.is_member):
            issues.append(_("Membership required to enroll in this course"))
        
        if not self.guest_purchase_allowed and (not partner or not partner.is_member):
            issues.append(_("Course is only available to members"))
        
        # Check if already enrolled
        if partner:
            existing_enrollment = self.channel_partner_ids.filtered(
                lambda p: p.partner_id == partner
            )
            if existing_enrollment:
                issues.append(_("Already enrolled in this course"))
        
        return {
            'eligible': len(issues) == 0,
            'issues': issues,
            'price': self.get_member_price(partner)
        }

    def get_course_summary(self):
        """Get course summary for website/portal display"""
        self.ensure_one()
        return {
            'name': self.name,
            'description': self.description,
            'category': dict(self._fields['course_category'].selection).get(self.course_category, ''),
            'level': dict(self._fields['course_level'].selection).get(self.course_level, ''),
            'difficulty': dict(self._fields['difficulty_level'].selection).get(self.difficulty_level, ''),
            'duration_hours': self.estimated_duration_hours,
            'total_slides': len(self.slide_ids),
            'ce_credits': self.ce_credits,
            'completion_rate': self.completion_rate,
            'total_enrollments': len(self.channel_partner_ids),
            'instructor': self.user_id.name,
            'rating': self.rating_avg,
        }

    # Constraints
    @api.constrains('ce_credits')
    def _check_ce_credits(self):
        """Validate CE credits"""
        for course in self:
            if course.ce_credits < 0:
                raise ValidationError(_("CE credits cannot be negative."))

    @api.constrains('member_price', 'non_member_price')
    def _check_pricing(self):
        """Validate pricing"""
        for course in self:
            if course.member_price < 0:
                raise ValidationError(_("Member price cannot be negative."))
            if course.non_member_price < 0:
                raise ValidationError(_("Non-member price cannot be negative."))

    @api.constrains('passing_score')
    def _check_passing_score(self):
        """Validate passing score"""
        for course in self:
            if course.passing_score < 0 or course.passing_score > 100:
                raise ValidationError(_("Passing score must be between 0 and 100."))

    @api.constrains('max_attempts')
    def _check_max_attempts(self):
        """Validate max attempts"""
        for course in self:
            if course.max_attempts < 1:
                raise ValidationError(_("Maximum attempts must be at least 1."))

    @api.constrains('access_duration_days')
    def _check_access_duration(self):
        """Validate access duration"""
        for course in self:
            if course.access_duration_days < 1:
                raise ValidationError(_("Access duration must be at least 1 day."))


class SlideChannelPartner(models.Model):
    _inherit = 'slide.channel.partner'

    # AMS Integration Fields
    enrollment_date = fields.Date('Enrollment Date', default=fields.Date.today)
    access_expiry_date = fields.Date('Access Expiry Date', compute='_compute_access_expiry_date', store=True)
    
    # CE Credits
    ce_credits_earned = fields.Float('CE Credits Earned', default=0.0)
    ce_credit_date = fields.Date('CE Credit Award Date')
    
    # AMS Certificate
    ams_certificate_issued = fields.Boolean('AMS Certificate Issued', default=False)
    ams_certificate_number = fields.Char('AMS Certificate Number')
    ams_certificate_date = fields.Date('AMS Certificate Date')
    ams_certificate_url = fields.Char('AMS Certificate URL')
    
    # Member Information
    is_member_enrollment = fields.Boolean('Member Enrollment', compute='_compute_member_status', store=True)
    member_type = fields.Char('Member Type', related='partner_id.member_type_id.name', readonly=True)
    
    # Progress Tracking Extensions
    first_access_date = fields.Datetime('First Access Date')
    last_activity_date = fields.Datetime('Last Activity Date')
    total_time_spent = fields.Float('Total Time Spent (Hours)', default=0.0)
    
    # Assessment Results
    best_quiz_score = fields.Float('Best Quiz Score (%)', default=0.0)
    quiz_attempts = fields.Integer('Quiz Attempts', default=0)
    passed_assessment = fields.Boolean('Passed Assessment', default=False)

    @api.depends('enrollment_date', 'channel_id.access_duration_days')
    def _compute_access_expiry_date(self):
        """Compute access expiry date"""
        for partner in self:
            if partner.enrollment_date and partner.channel_id.access_duration_days:
                from datetime import timedelta
                partner.access_expiry_date = partner.enrollment_date + timedelta(
                    days=partner.channel_id.access_duration_days
                )
            else:
                partner.access_expiry_date = False

    @api.depends('partner_id.is_member')
    def _compute_member_status(self):
        """Compute member enrollment status"""
        for partner in self:
            partner.is_member_enrollment = partner.partner_id.is_member

    # Override completion to handle CE credits
    def write(self, vals):
        """Override to handle CE credit awarding"""
        result = super().write(vals)
        
        # Award CE credits when course is completed
        if 'completed' in vals and vals['completed']:
            for partner in self.filtered(lambda p: p.channel_id.ce_credits > 0):
                if not partner.ce_credits_earned:
                    partner.write({
                        'ce_credits_earned': partner.channel_id.ce_credits,
                        'ce_credit_date': fields.Date.today()
                    })
        
        return result

    # Action Methods
    def action_issue_ams_certificate(self):
        """Issue AMS certificate"""
        self.ensure_one()
        
        if not self.completed:
            raise UserError(_("Course must be completed to issue certificate."))
        
        if self.ams_certificate_issued:
            raise UserError(_("Certificate has already been issued."))
        
        # Generate certificate number
        cert_number = self._generate_certificate_number()
        
        self.write({
            'ams_certificate_issued': True,
            'ams_certificate_number': cert_number,
            'ams_certificate_date': fields.Date.today(),
            'ams_certificate_url': f'/course/certificate/{self.id}/{cert_number}'
        })
        
        # Send certificate email
        self._send_certificate_email()

    def action_extend_access(self):
        """Extend course access"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Extend Course Access'),
            'res_model': 'ams.course.access.extension.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_enrollment_id': self.id,
            }
        }

    def action_reset_progress(self):
        """Reset course progress"""
        self.ensure_one()
        
        # Reset slide progress
        slide_partners = self.env['slide.slide.partner'].search([
            ('channel_id', '=', self.channel_id.id),
            ('partner_id', '=', self.partner_id.id)
        ])
        slide_partners.unlink()
        
        # Reset AMS progress
        self.write({
            'completed': False,
            'completion': 0,
            'ce_credits_earned': 0.0,
            'ce_credit_date': False,
            'ams_certificate_issued': False,
            'ams_certificate_number': False,
            'ams_certificate_date': False,
            'best_quiz_score': 0.0,
            'quiz_attempts': 0,
            'passed_assessment': False,
        })

    def action_download_certificate(self):
        """Download AMS certificate"""
        self.ensure_one()
        
        if not self.ams_certificate_issued:
            raise UserError(_("No certificate available for download."))
        
        return {
            'type': 'ir.actions.act_url',
            'url': self.ams_certificate_url,
            'target': 'new'
        }

    # Helper Methods
    def _generate_certificate_number(self):
        """Generate unique certificate number"""
        sequence = self.env['ir.sequence'].next_by_code('ams.certificate.number')
        return sequence or f"CERT-{self.id:06d}"

    def _send_certificate_email(self):
        """Send certificate email notification"""
        # This would integrate with email templates
        self.partner_id.message_post(
            body=_("Certificate issued for course: %s (Certificate #%s)") % (
                self.channel_id.name,
                self.ams_certificate_number
            ),
            subject=_("Course Certificate Issued"),
            message_type='notification'
        )

    def check_access_validity(self):
        """Check if access is still valid"""
        self.ensure_one()
        
        if not self.access_expiry_date:
            return True
        
        return fields.Date.today() <= self.access_expiry_date

    def get_progress_summary(self):
        """Get progress summary for portal display"""
        self.ensure_one()
        return {
            'course_name': self.channel_id.name,
            'progress_percentage': self.completion,
            'completed': self.completed,
            'slides_done': len(self.slide_partner_ids.filtered('completed')),
            'total_slides': len(self.channel_id.slide_ids),
            'ce_credits_earned': self.ce_credits_earned,
            'certificate_available': self.ams_certificate_issued,
            'access_expires': self.access_expiry_date,
            'time_spent': self.total_time_spent,
            'best_score': self.best_quiz_score,
        }

    # Automated Processing
    @api.model
    def process_access_expiry(self):
        """Cron job to process expired course access"""
        _logger.info("Processing expired course access...")
        
        today = fields.Date.today()
        expired_enrollments = self.search([
            ('access_expiry_date', '<', today),
            ('completed', '=', False)
        ])
        
        # Here you could implement logic to handle expired access
        # For example, send reminder emails, disable access, etc.
        
        _logger.info(f"Found {len(expired_enrollments)} expired course enrollments")

    def name_get(self):
        """Custom name display"""
        result = []
        for record in self:
            name = f"{record.partner_id.name} - {record.channel_id.name}"
            if record.completed:
                name += " (Completed)"
            result.append((record.id, name))
        return result