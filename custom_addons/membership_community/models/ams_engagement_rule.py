# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from datetime import date, datetime, timedelta
import logging

_logger = logging.getLogger(__name__)


class AMSEngagementRule(models.Model):
    _name = 'ams.engagement.rule'
    _description = 'Member Engagement Scoring Rules'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'sequence, name'

    # Basic Information
    name = fields.Char('Rule Name', required=True, tracking=True)
    rule_code = fields.Char('Rule Code', required=True, tracking=True)
    description = fields.Text('Description', 
                            help="Describe when and how this engagement rule should be applied")
    sequence = fields.Integer('Sequence', default=10, help="Order of rule evaluation")
    active = fields.Boolean('Active', default=True, tracking=True)

    # Rule Configuration
    rule_type = fields.Selection([
        ('event_attendance', 'Event Attendance'),
        ('event_speaking', 'Event Speaking'),
        ('event_organizing', 'Event Organizing'),
        ('portal_login', 'Portal Login'),
        ('profile_update', 'Profile Update'),
        ('document_access', 'Document Access'),
        ('email_engagement', 'Email Engagement'),
        ('newsletter_engagement', 'Newsletter Engagement'),
        ('survey_participation', 'Survey Participation'),
        ('committee_participation', 'Committee Participation'),
        ('volunteer_activity', 'Volunteer Activity'),
        ('early_renewal', 'Early Renewal'),
        ('payment_method', 'Payment Method'),
        ('referral', 'Member Referral'),
        ('certification_earned', 'Certification Earned'),
        ('continuing_education', 'Continuing Education'),
        ('manual_override', 'Manual Override'),
        ('special_recognition', 'Special Recognition')
    ], string='Rule Type', required=True, tracking=True)

    points_value = fields.Float('Points Value', required=True, default=1.0,
                              help="Base points awarded when rule is triggered")

    # Frequency and Limits
    frequency_limit = fields.Boolean('Has Frequency Limit', default=False,
                                   help="Limit how often this rule can be applied")
    time_period = fields.Selection([
        ('day', 'Per Day'),
        ('week', 'Per Week'),
        ('month', 'Per Month'),
        ('quarter', 'Per Quarter'),
        ('year', 'Per Year')
    ], string='Time Period', help="Time period for frequency limit")
    
    max_points_per_period = fields.Float('Max Points Per Period', default=0.0,
                                       help="Maximum points that can be earned in the time period")
    reset_frequency = fields.Selection([
        ('never', 'Never Reset'),
        ('monthly', 'Reset Monthly'),
        ('quarterly', 'Reset Quarterly'),
        ('annually', 'Reset Annually')
    ], string='Reset Frequency', default='never',
       help="How often the frequency counter resets")

    # Conditions and Filters
    member_type_ids = fields.Many2many('ams.member.type', string='Applicable Member Types',
                                     help="Leave empty to apply to all member types")
    apply_to_all_members = fields.Boolean('Apply to All Members', default=True,
                                        help="Apply rule regardless of member type")
    min_membership_duration = fields.Integer('Minimum Membership Duration (Days)', default=0,
                                           help="Minimum days as member before rule applies")
    requires_approval = fields.Boolean('Requires Approval', default=False,
                                     help="Manual approval required before points are awarded")

    # Date Range
    start_date = fields.Date('Start Date', help="Rule becomes effective on this date")
    end_date = fields.Date('End Date', help="Rule expires on this date")
    auto_expire = fields.Boolean('Auto Expire', default=False,
                                help="Automatically deactivate when end date is reached")

    # Event-specific Conditions
    event_category_filter = fields.Boolean('Filter by Event Category', default=False)
    event_categories = fields.Char('Event Categories', help="Event categories (free text for now)")
    min_event_hours = fields.Float('Minimum Event Hours', default=0.0)
    ce_credit_multiplier = fields.Float('CE Credit Multiplier', default=1.0,
                                      help="Multiply points by CE credits earned")

    # Communication-specific Conditions
    email_open_points = fields.Float('Email Open Points', default=0.5)
    email_click_points = fields.Float('Email Click Points', default=1.0)
    survey_completion_points = fields.Float('Survey Completion Points', default=2.0)

    # Portal Activity Conditions
    login_streak_bonus = fields.Float('Login Streak Bonus', default=0.0,
                                    help="Bonus points for consecutive day logins")
    profile_completeness_bonus = fields.Float('Profile Completeness Bonus', default=0.0,
                                            help="Bonus for complete profile information")
    document_download_points = fields.Float('Document Download Points', default=0.1)

    # Payment and Renewal Conditions
    early_renewal_days = fields.Integer('Early Renewal Days', default=60,
                                      help="Days before expiration to qualify as early renewal")
    auto_pay_bonus = fields.Float('Auto Pay Bonus', default=2.0,
                                help="Bonus points for setting up automatic payment")
    loyalty_year_bonus = fields.Float('Loyalty Year Bonus', default=1.0,
                                    help="Additional points per year of continuous membership")

    # Advanced Configuration
    calculation_formula = fields.Selection([
        ('fixed', 'Fixed Points'),
        ('percentage', 'Percentage Based'),
        ('tiered', 'Tiered Scoring'),
        ('custom', 'Custom Formula')
    ], string='Calculation Method', default='fixed')
    
    use_custom_formula = fields.Boolean('Use Custom Formula', default=False)
    custom_python_code = fields.Text('Custom Python Code',
                                    help="Python code for custom point calculation")

    # Integration Settings
    external_system_sync = fields.Boolean('External System Sync', default=False)
    api_endpoint = fields.Char('API Endpoint', help="External API endpoint for data sync")
    webhook_trigger = fields.Boolean('Webhook Trigger', default=False,
                                   help="Trigger webhook when rule is applied")

    # Statistics and Tracking
    times_applied = fields.Integer('Times Applied', readonly=True, default=0)
    total_points_awarded = fields.Float('Total Points Awarded', readonly=True, default=0.0)
    average_points_per_application = fields.Float('Average Points Per Application', 
                                                 compute='_compute_average_points', store=True)
    last_applied = fields.Datetime('Last Applied', readonly=True)
    unique_members_affected = fields.Integer('Unique Members Affected', readonly=True, default=0)
    most_recent_application = fields.Datetime('Most Recent Application', readonly=True)

    # Related Records
    application_ids = fields.One2many('ams.engagement.application', 'rule_id', 'Applications')

    @api.depends('times_applied', 'total_points_awarded')
    def _compute_average_points(self):
        """Compute average points per application"""
        for rule in self:
            if rule.times_applied > 0:
                rule.average_points_per_application = rule.total_points_awarded / rule.times_applied
            else:
                rule.average_points_per_application = 0.0

    @api.model
    def create(self, vals):
        """Override create to handle rule code generation"""
        if not vals.get('rule_code'):
            vals['rule_code'] = self.env['ir.sequence'].next_by_code('ams.engagement.rule')
        
        # Ensure rule code is uppercase
        if vals.get('rule_code'):
            vals['rule_code'] = vals['rule_code'].upper()
        
        return super().create(vals)

    def write(self, vals):
        """Override write to handle rule code updates"""
        if 'rule_code' in vals and vals['rule_code']:
            vals['rule_code'] = vals['rule_code'].upper()
        
        return super().write(vals)

    def name_get(self):
        """Custom name_get to show rule code"""
        result = []
        for record in self:
            if record.rule_code:
                name = f"{record.name} ({record.rule_code})"
            else:
                name = record.name
            result.append((record.id, name))
        return result

    def check_rule_conditions(self, partner, context_data=None):
        """Check if rule conditions are met for a partner"""
        self.ensure_one()
        
        if context_data is None:
            context_data = {}

        # Check if rule is active and within date range
        if not self.active:
            return False, _("Rule is not active")
        
        today = fields.Date.today()
        if self.start_date and today < self.start_date:
            return False, _("Rule is not yet effective")
        
        if self.end_date and today > self.end_date:
            return False, _("Rule has expired")

        # Check member type eligibility
        if not self.apply_to_all_members and self.member_type_ids:
            if partner.member_type_id not in self.member_type_ids:
                return False, _("Member type not eligible for this rule")

        # Check membership duration
        if self.min_membership_duration > 0 and partner.membership_start_date:
            membership_days = (today - partner.membership_start_date).days
            if membership_days < self.min_membership_duration:
                return False, _("Minimum membership duration not met")

        # Check member status
        if partner.member_status not in ['active', 'grace']:
            return False, _("Member is not active")

        # Check frequency limits
        if self.frequency_limit and self.time_period:
            if self._check_frequency_limit_exceeded(partner):
                return False, _("Frequency limit exceeded for this period")

        return True, _("All conditions met")

    def _check_frequency_limit_exceeded(self, partner):
        """Check if frequency limit is exceeded for this partner"""
        self.ensure_one()
        
        if not self.frequency_limit or not self.time_period or self.max_points_per_period <= 0:
            return False

        # Calculate period start date
        today = fields.Date.today()
        if self.time_period == 'day':
            period_start = today
        elif self.time_period == 'week':
            period_start = today - timedelta(days=today.weekday())
        elif self.time_period == 'month':
            period_start = today.replace(day=1)
        elif self.time_period == 'quarter':
            quarter_month = ((today.month - 1) // 3) * 3 + 1
            period_start = today.replace(month=quarter_month, day=1)
        elif self.time_period == 'year':
            period_start = today.replace(month=1, day=1)
        else:
            return False

        # Check points awarded in this period
        applications = self.env['ams.engagement.application'].search([
            ('rule_id', '=', self.id),
            ('partner_id', '=', partner.id),
            ('application_date', '>=', period_start),
            ('status', '=', 'approved')
        ])
        
        total_points = sum(applications.mapped('points_awarded'))
        return total_points >= self.max_points_per_period

    def calculate_points(self, partner, context_data=None):
        """Calculate points based on rule configuration"""
        self.ensure_one()
        
        if context_data is None:
            context_data = {}

        base_points = self.points_value

        # Apply calculation formula
        if self.calculation_formula == 'fixed':
            calculated_points = base_points
        elif self.calculation_formula == 'percentage':
            # Implement percentage-based calculation
            calculated_points = base_points  # Placeholder
        elif self.calculation_formula == 'tiered':
            # Implement tiered calculation
            calculated_points = base_points  # Placeholder
        elif self.calculation_formula == 'custom' and self.use_custom_formula:
            # Implement custom formula execution
            calculated_points = self._execute_custom_formula(partner, context_data)
        else:
            calculated_points = base_points

        # Apply multipliers and bonuses
        if self.rule_type in ['event_attendance', 'event_speaking'] and self.ce_credit_multiplier != 1.0:
            ce_credits = context_data.get('ce_credits', 1.0)
            calculated_points *= (ce_credits * self.ce_credit_multiplier)

        if self.rule_type == 'early_renewal' and self.loyalty_year_bonus > 0:
            membership_years = self._calculate_membership_years(partner)
            calculated_points += (membership_years * self.loyalty_year_bonus)

        return max(0, calculated_points)  # Ensure non-negative points

    def _execute_custom_formula(self, partner, context_data):
        """Execute custom Python formula safely"""
        self.ensure_one()
        
        if not self.custom_python_code:
            return self.points_value

        try:
            # Create safe execution environment
            safe_dict = {
                'partner': partner,
                'context': context_data,
                'base_points': self.points_value,
                'membership_years': self._calculate_membership_years(partner),
                'max': max,
                'min': min,
                'round': round,
                'abs': abs
            }
            
            # Execute custom code
            exec(self.custom_python_code, {"__builtins__": {}}, safe_dict)
            result = safe_dict.get('result', self.points_value)
            
            return float(result) if result is not None else self.points_value
            
        except Exception as e:
            _logger.error(f"Error executing custom formula for rule {self.name}: {str(e)}")
            return self.points_value

    def _calculate_membership_years(self, partner):
        """Calculate years of continuous membership"""
        if not partner.membership_start_date:
            return 0
        
        today = fields.Date.today()
        years = (today - partner.membership_start_date).days / 365.25
        return max(0, years)

    def apply_rule(self, partner, context_data=None):
        """Apply rule to a partner and create application record"""
        self.ensure_one()
        
        # Check conditions
        conditions_met, message = self.check_rule_conditions(partner, context_data)
        if not conditions_met:
            return False, message

        # Calculate points
        points = self.calculate_points(partner, context_data)
        
        # Create application record
        application = self.env['ams.engagement.application'].create({
            'rule_id': self.id,
            'partner_id': partner.id,
            'points_awarded': points,
            'application_date': fields.Datetime.now(),
            'status': 'pending' if self.requires_approval else 'approved',
            'context_data': str(context_data) if context_data else '',
            'notes': f"Applied rule: {self.name}"
        })

        # Update partner engagement score if approved
        if not self.requires_approval:
            partner.engagement_score += points
            application.status = 'approved'

        # Update rule statistics
        self._update_statistics(points)
        
        return True, f"Rule applied successfully. Points awarded: {points}"

    def _update_statistics(self, points_awarded):
        """Update rule application statistics"""
        self.ensure_one()
        self.write({
            'times_applied': self.times_applied + 1,
            'total_points_awarded': self.total_points_awarded + points_awarded,
            'last_applied': fields.Datetime.now(),
            'most_recent_application': fields.Datetime.now()
        })

    def action_view_applications(self):
        """View applications for this rule"""
        self.ensure_one()
        return {
            'name': _('Applications: %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'ams.engagement.application',
            'view_mode': 'list,form',
            'domain': [('rule_id', '=', self.id)],
            'context': {'default_rule_id': self.id},
        }

    def action_test_rule(self):
        """Test rule with sample data"""
        self.ensure_one()
        # This would open a wizard to test the rule
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Rule Test'),
                'message': _('Rule testing wizard will be available in future updates.'),
                'type': 'info'
            }
        }

    @api.model
    def cleanup_old_engagement_data(self):
        """Cron job to cleanup old engagement data"""
        _logger.info("Starting engagement data cleanup...")
        
        try:
            # Cleanup old application records (older than 2 years)
            cutoff_date = fields.Date.today() - timedelta(days=730)
            old_applications = self.env['ams.engagement.application'].search([
                ('application_date', '<', cutoff_date),
                ('status', 'in', ['approved', 'rejected'])
            ])
            
            count = len(old_applications)
            old_applications.unlink()
            
            _logger.info(f"Cleaned up {count} old engagement applications")
            
        except Exception as e:
            _logger.error(f"Error in engagement data cleanup: {str(e)}")

    # Constraints and Validations
    @api.constrains('rule_code')
    def _check_rule_code_unique(self):
        """Ensure rule codes are unique"""
        for record in self:
            if record.rule_code:
                existing = self.search([
                    ('rule_code', '=', record.rule_code),
                    ('id', '!=', record.id)
                ])
                if existing:
                    raise ValidationError(_("Rule code must be unique. '%s' already exists.") % record.rule_code)

    @api.constrains('points_value')
    def _check_points_value(self):
        """Validate points value"""
        for record in self:
            if record.points_value < 0:
                raise ValidationError(_("Points value cannot be negative."))
            if record.points_value > 1000:
                raise ValidationError(_("Points value seems excessive (>1000)."))

    @api.constrains('max_points_per_period')
    def _check_max_points_per_period(self):
        """Validate max points per period"""
        for record in self:
            if record.frequency_limit and record.max_points_per_period < 0:
                raise ValidationError(_("Max points per period cannot be negative."))

    @api.constrains('start_date', 'end_date')
    def _check_date_range(self):
        """Validate date range"""
        for record in self:
            if record.start_date and record.end_date:
                if record.end_date <= record.start_date:
                    raise ValidationError(_("End date must be after start date."))

    @api.constrains('min_membership_duration')
    def _check_membership_duration(self):
        """Validate minimum membership duration"""
        for record in self:
            if record.min_membership_duration < 0:
                raise ValidationError(_("Minimum membership duration cannot be negative."))

    def copy(self, default=None):
        """Override copy to handle unique code"""
        if default is None:
            default = {}
        if 'rule_code' not in default:
            default['rule_code'] = f"{self.rule_code}_COPY"
        if 'name' not in default:
            default['name'] = _("%s (copy)") % self.name
        return super().copy(default)


class AMSEngagementApplication(models.Model):
    _name = 'ams.engagement.application'
    _description = 'Engagement Rule Application Record'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'application_date desc'

    rule_id = fields.Many2one('ams.engagement.rule', 'Engagement Rule', required=True)
    partner_id = fields.Many2one('res.partner', 'Member', required=True)
    
    points_awarded = fields.Float('Points Awarded', required=True)
    application_date = fields.Datetime('Application Date', default=fields.Datetime.now, required=True)
    
    status = fields.Selection([
        ('pending', 'Pending Approval'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected')
    ], string='Status', default='pending', tracking=True)
    
    context_data = fields.Text('Context Data', help="Additional context information")
    notes = fields.Text('Notes')
    
    # Approval tracking
    approved_by = fields.Many2one('res.users', 'Approved By', readonly=True)
    approval_date = fields.Datetime('Approval Date', readonly=True)
    rejection_reason = fields.Text('Rejection Reason')

    def action_approve(self):
        """Approve application and award points"""
        for application in self:
            if application.status != 'pending':
                continue
            
            application.write({
                'status': 'approved',
                'approved_by': self.env.user.id,
                'approval_date': fields.Datetime.now()
            })
            
            # Award points to member
            application.partner_id.engagement_score += application.points_awarded

    def action_reject(self):
        """Reject application"""
        for application in self:
            if application.status != 'pending':
                continue
            
            application.write({
                'status': 'rejected'
            })