# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
import logging

_logger = logging.getLogger(__name__)


class AMSMembershipCourse(models.Model):
    _name = 'ams.membership.course'
    _description = 'Educational Courses and Training Programs'
    _inherit = 'ams.membership.base'
    _rec_name = 'name'

    # Course Classification
    course_type = fields.Selection([
        ('online', 'Online Course'),
        ('in_person', 'In-Person Training'),
        ('hybrid', 'Hybrid Learning'),
        ('self_paced', 'Self-Paced Study'),
        ('webinar', 'Webinar Series'),
        ('workshop', 'Workshop'),
        ('certification', 'Certification Program'),
        ('continuing_education', 'Continuing Education'),
        ('conference', 'Conference Access')
    ], string='Course Type', default='online', required=True)
    
    # Course Content and Structure
    course_level = fields.Selection([
        ('beginner', 'Beginner'),
        ('intermediate', 'Intermediate'),
        ('advanced', 'Advanced'),
        ('expert', 'Expert'),
        ('all_levels', 'All Levels')
    ], string='Course Level', default='intermediate')
    
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
    ], string='Course Category', default='professional_development')
    
    # Duration and Schedule
    total_duration_hours = fields.Float('Total Duration (Hours)', default=0.0)
    estimated_completion_time = fields.Float('Estimated Completion (Days)', default=30.0)
    
    # Access and Completion
    access_start_date = fields.Date('Access Start Date', default=fields.Date.today)
    access_end_date = fields.Date('Access End Date')
    access_duration_days = fields.Integer('Access Duration (Days)', default=365,
                                        help="Days of access from start date")
    
    # Progress Tracking
    enrollment_date = fields.Date('Enrollment Date', default=fields.Date.today)
    first_access_date = fields.Date('First Access Date', readonly=True)
    last_access_date = fields.Datetime('Last Access Date', readonly=True)
    completion_date = fields.Date('Completion Date', readonly=True)
    
    progress_percentage = fields.Float('Progress Percentage', default=0.0, readonly=True)
    modules_completed = fields.Integer('Modules Completed', default=0, readonly=True)
    total_modules = fields.Integer('Total Modules', default=0)
    
    # Completion and Certification
    completion_status = fields.Selection([
        ('not_started', 'Not Started'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('expired', 'Expired'),
        ('failed', 'Failed')
    ], string='Completion Status', default='not_started', readonly=True)
    
    passing_score = fields.Float('Passing Score (%)', default=70.0)
    final_score = fields.Float('Final Score (%)', default=0.0, readonly=True)
    passed = fields.Boolean('Passed', readonly=True)
    
    # Continuing Education Credits
    ce_credits_available = fields.Float('CE Credits Available', default=0.0)
    ce_credits_earned = fields.Float('CE Credits Earned', default=0.0, readonly=True)
    ce_provider = fields.Char('CE Provider')
    ce_approval_number = fields.Char('CE Approval Number')
    
    # Certificates and Documentation
    certificate_issued = fields.Boolean('Certificate Issued', readonly=True)
    certificate_number = fields.Char('Certificate Number', readonly=True)
    certificate_issue_date = fields.Date('Certificate Issue Date', readonly=True)
    certificate_expiry_date = fields.Date('Certificate Expiry Date', readonly=True)
    
    # Instructor and Support
    instructor_id = fields.Many2one('res.partner', 'Instructor',
                                  domain=[('is_company', '=', False)])
    instructor_email = fields.Char('Instructor Email', related='instructor_id.email', readonly=True)
    support_contact = fields.Many2one('res.partner', 'Support Contact')
    
    # Platform and Technical
    learning_platform = fields.Selection([
        ('internal', 'Internal Platform'),
        ('external', 'External Platform'),
        ('zoom', 'Zoom'),
        ('teams', 'Microsoft Teams'),
        ('webex', 'Cisco WebEx'),
        ('lms', 'Learning Management System'),
        ('youtube', 'YouTube'),
        ('vimeo', 'Vimeo')
    ], string='Learning Platform', default='internal')
    
    access_url = fields.Url('Course Access URL')
    login_credentials = fields.Text('Login Credentials', groups="ams_foundation.group_ams_staff")
    
    # Assessments and Evaluations
    assessment_required = fields.Boolean('Assessment Required', default=True)
    number_of_attempts = fields.Integer('Number of Attempts', default=0, readonly=True)
    max_attempts = fields.Integer('Maximum Attempts', default=3)
    
    # Course Materials
    materials_included = fields.Text('Course Materials Included')
    prerequisites = fields.Text('Prerequisites')
    learning_objectives = fields.Text('Learning Objectives')
    
    # Feedback and Evaluation
    course_rating = fields.Float('Course Rating', default=0.0, readonly=True)
    feedback_provided = fields.Boolean('Feedback Provided', readonly=True)
    instructor_rating = fields.Float('Instructor Rating', default=0.0, readonly=True)
    
    # Networking and Collaboration
    discussion_forum_access = fields.Boolean('Discussion Forum Access', default=True)
    peer_networking_enabled = fields.Boolean('Peer Networking Enabled', default=True)
    study_group_access = fields.Boolean('Study Group Access', default=False)

    @api.onchange('enrollment_date', 'access_duration_days')
    def _onchange_enrollment_date(self):
        """Calculate access end date based on enrollment and duration"""
        if self.enrollment_date and self.access_duration_days:
            from datetime import timedelta
            self.access_end_date = self.enrollment_date + timedelta(days=self.access_duration_days)

    @api.onchange('course_type')
    def _onchange_course_type(self):
        """Set defaults based on course type"""
        if self.course_type == 'webinar':
            self.learning_platform = 'zoom'
            self.total_duration_hours = 1.0
            self.estimated_completion_time = 1.0
            self.assessment_required = False
        elif self.course_type == 'certification':
            self.assessment_required = True
            self.passing_score = 80.0
            self.max_attempts = 3
            self.ce_credits_available = 10.0
        elif self.course_type == 'self_paced':
            self.learning_platform = 'lms'
            self.estimated_completion_time = 30.0
            self.access_duration_days = 365

    # Action Methods
    def action_start_course(self):
        """Start the course"""
        self.ensure_one()
        
        if self.completion_status != 'not_started':
            raise UserError(_("Course has already been started."))
        
        if self.state not in ['active', 'grace']:
            raise UserError(_("Course subscription must be active to start."))
        
        self.write({
            'completion_status': 'in_progress',
            'first_access_date': fields.Date.today(),
            'last_access_date': fields.Datetime.now()
        })
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Course Started'),
                'message': _('You have successfully started the course. Good luck!'),
                'type': 'success'
            }
        }

    def action_access_course(self):
        """Access course content"""
        self.ensure_one()
        
        if self.state not in ['active', 'grace']:
            raise UserError(_("Course subscription must be active to access content."))
        
        today = fields.Date.today()
        if self.access_end_date and today > self.access_end_date:
            raise UserError(_("Course access has expired."))
        
        # Update access tracking
        self.write({
            'last_access_date': fields.Datetime.now(),
            'first_access_date': self.first_access_date or fields.Date.today()
        })
        
        if self.completion_status == 'not_started':
            self.completion_status = 'in_progress'
        
        # Redirect to course platform
        if self.access_url:
            return {
                'type': 'ir.actions.act_url',
                'url': self.access_url,
                'target': 'new'
            }
        else:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Course Access'),
                    'message': _('Course access URL will be provided by the instructor.'),
                    'type': 'info'
                }
            }

    def action_submit_assessment(self):
        """Submit course assessment"""
        self.ensure_one()
        
        if not self.assessment_required:
            raise UserError(_("This course does not require an assessment."))
        
        if self.number_of_attempts >= self.max_attempts:
            raise UserError(_("Maximum number of attempts reached."))
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Submit Assessment'),
            'res_model': 'ams.course.assessment.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_course_id': self.id,
            }
        }

    def action_record_completion(self, score=None, passed=None):
        """Record course completion"""
        self.ensure_one()
        
        completion_vals = {
            'completion_date': fields.Date.today(),
            'completion_status': 'completed' if passed else 'failed',
            'progress_percentage': 100.0 if passed else self.progress_percentage
        }
        
        if score is not None:
            completion_vals['final_score'] = score
            completion_vals['passed'] = score >= self.passing_score
        
        if passed is not None:
            completion_vals['passed'] = passed
        
        # Award CE credits if passed
        if completion_vals.get('passed', False) and self.ce_credits_available > 0:
            completion_vals['ce_credits_earned'] = self.ce_credits_available
        
        self.write(completion_vals)
        
        # Generate certificate if passed
        if completion_vals.get('passed', False):
            self._generate_certificate()

    def action_issue_certificate(self):
        """Issue course completion certificate"""
        self.ensure_one()
        
        if not self.passed:
            raise UserError(_("Certificate can only be issued for passed courses."))
        
        if self.certificate_issued:
            raise UserError(_("Certificate has already been issued."))
        
        self._generate_certificate()
        
        return {
            'type': 'ir.actions.report',
            'report_name': 'ams_membership_core.course_certificate_report',
            'report_type': 'qweb-pdf',
            'data': {'course_id': self.id},
            'context': {'active_id': self.id},
        }

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
                'default_course_id': self.id,
            }
        }

    def action_provide_feedback(self):
        """Provide course feedback"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Course Feedback'),
            'res_model': 'ams.course.feedback.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_course_id': self.id,
            }
        }

    def action_view_transcript(self):
        """View course transcript"""
        self.ensure_one()
        return {
            'type': 'ir.actions.report',
            'report_name': 'ams_membership_core.course_transcript_report',
            'report_type': 'qweb-pdf',
            'data': {'course_id': self.id},
            'context': {'active_id': self.id},
        }

    # Course Management Methods
    def update_progress(self, modules_completed=None, percentage=None):
        """Update course progress"""
        self.ensure_one()
        
        update_vals = {}
        
        if modules_completed is not None:
            update_vals['modules_completed'] = modules_completed
            if self.total_modules > 0:
                update_vals['progress_percentage'] = (modules_completed / self.total_modules) * 100
        
        if percentage is not None:
            update_vals['progress_percentage'] = min(percentage, 100.0)
        
        # Update completion status based on progress
        if update_vals.get('progress_percentage', self.progress_percentage) >= 100:
            update_vals['completion_status'] = 'completed'
            update_vals['completion_date'] = fields.Date.today()
        elif update_vals.get('progress_percentage', self.progress_percentage) > 0:
            update_vals['completion_status'] = 'in_progress'
        
        self.write(update_vals)

    def record_assessment_attempt(self, score):
        """Record an assessment attempt"""
        self.ensure_one()
        
        self.write({
            'number_of_attempts': self.number_of_attempts + 1,
            'final_score': score,
            'passed': score >= self.passing_score
        })
        
        # If passed, complete the course
        if score >= self.passing_score:
            self.action_record_completion(score=score, passed=True)

    def _generate_certificate(self):
        """Generate completion certificate"""
        self.ensure_one()
        
        import secrets
        certificate_number = f"CERT-{self.id:06d}-{secrets.token_hex(4).upper()}"
        
        certificate_vals = {
            'certificate_issued': True,
            'certificate_number': certificate_number,
            'certificate_issue_date': fields.Date.today()
        }
        
        # Set expiry date if CE credits are involved
        if self.ce_credits_available > 0:
            from datetime import timedelta
            certificate_vals['certificate_expiry_date'] = fields.Date.today() + timedelta(days=365*2)  # 2 years
        
        self.write(certificate_vals)
        
        # Log certificate generation
        self.message_post(
            body=_("Certificate issued: %s") % certificate_number,
            message_type='notification'
        )

    def check_access_eligibility(self):
        """Check if user can access course content"""
        self.ensure_one()
        
        issues = []
        
        if self.state not in ['active', 'grace']:
            issues.append(_("Course subscription must be active"))
        
        today = fields.Date.today()
        if self.access_start_date and today < self.access_start_date:
            issues.append(_("Course access has not started yet"))
        
        if self.access_end_date and today > self.access_end_date:
            issues.append(_("Course access has expired"))
        
        if self.completion_status == 'expired':
            issues.append(_("Course has expired"))
        
        return {
            'eligible': len(issues) == 0,
            'issues': issues
        }

    def get_course_summary(self):
        """Get course summary for portal"""
        self.ensure_one()
        return {
            'type': dict(self._fields['course_type'].selection)[self.course_type],
            'level': dict(self._fields['course_level'].selection)[self.course_level],
            'category': dict(self._fields['course_category'].selection)[self.course_category],
            'duration_hours': self.total_duration_hours,
            'progress': self.progress_percentage,
            'status': dict(self._fields['completion_status'].selection)[self.completion_status],
            'ce_credits': self.ce_credits_available,
            'access_expires': self.access_end_date,
            'passed': self.passed,
            'certificate_issued': self.certificate_issued,
        }

    # Automated Processing
    @api.model
    def process_course_expiry(self):
        """Cron job to process course access expiry"""
        _logger.info("Starting course access expiry processing...")
        
        today = fields.Date.today()
        
        try:
            # Find courses with expired access
            expired_courses = self.search([
                ('state', 'in', ['active', 'grace']),
                ('access_end_date', '<', today),
                ('completion_status', '!=', 'expired')
            ])
            
            for course in expired_courses:
                course.write({
                    'completion_status': 'expired'
                })
            
            _logger.info(f"Processed {len(expired_courses)} expired course accesses")
            
        except Exception as e:
            _logger.error(f"Error in course expiry processing: {str(e)}")

    # Constraints
    @api.constrains('product_id')
    def _check_product_class(self):
        """Ensure product is a course product"""
        for course in self:
            if course.product_id.product_tmpl_id.product_class != 'courses':
                raise ValidationError(_("Product must be a courses product class."))

    @api.constrains('progress_percentage')
    def _check_progress_percentage(self):
        """Validate progress percentage"""
        for course in self:
            if course.progress_percentage < 0 or course.progress_percentage > 100:
                raise ValidationError(_("Progress percentage must be between 0 and 100."))

    @api.constrains('final_score', 'passing_score')
    def _check_scores(self):
        """Validate scores"""
        for course in self:
            if course.final_score < 0 or course.final_score > 100:
                raise ValidationError(_("Final score must be between 0 and 100."))
            if course.passing_score < 0 or course.passing_score > 100:
                raise ValidationError(_("Passing score must be between 0 and 100."))

    @api.constrains('number_of_attempts', 'max_attempts')
    def _check_attempts(self):
        """Validate attempt counts"""
        for course in self:
            if course.number_of_attempts < 0:
                raise ValidationError(_("Number of attempts cannot be negative."))
            if course.max_attempts < 1:
                raise ValidationError(_("Maximum attempts must be at least 1."))

    @api.constrains('modules_completed', 'total_modules')
    def _check_modules(self):
        """Validate module counts"""
        for course in self:
            if course.modules_completed < 0:
                raise ValidationError(_("Modules completed cannot be negative."))
            if course.total_modules < 0:
                raise ValidationError(_("Total modules cannot be negative."))
            if course.modules_completed > course.total_modules:
                raise ValidationError(_("Modules completed cannot exceed total modules."))

    @api.constrains('ce_credits_available', 'ce_credits_earned')
    def _check_ce_credits(self):
        """Validate CE credits"""
        for course in self:
            if course.ce_credits_available < 0:
                raise ValidationError(_("CE credits available cannot be negative."))
            if course.ce_credits_earned < 0:
                raise ValidationError(_("CE credits earned cannot be negative."))
            if course.ce_credits_earned > course.ce_credits_available:
                raise ValidationError(_("CE credits earned cannot exceed available credits."))

    @api.constrains('enrollment_date', 'access_start_date', 'access_end_date')
    def _check_course_dates(self):
        """Validate course dates"""
        for course in self:
            if course.access_start_date and course.access_end_date:
                if course.access_end_date <= course.access_start_date:
                    raise ValidationError(_("Access end date must be after start date."))
            
            if course.enrollment_date and course.access_start_date:
                if course.enrollment_date > course.access_start_date:
                    raise ValidationError(_("Enrollment date cannot be after access start date."))