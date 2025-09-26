# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
import logging

_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _inherit = 'res.partner'

    # Membership Relationships
    membership_ids = fields.One2many('ams.membership.membership', 'partner_id', 'Memberships')
    chapter_membership_ids = fields.One2many('ams.membership.chapter', 'partner_id', 'Chapter Memberships')
    subscription_ids = fields.One2many('ams.membership.subscription', 'partner_id', 'Subscriptions')
    course_ids = fields.One2many('ams.membership.course', 'partner_id', 'Courses')
    donation_ids = fields.One2many('ams.membership.donation', 'partner_id', 'Donations')
    
    # Aggregate Membership Information
    active_membership_count = fields.Integer('Active Memberships', compute='_compute_membership_stats')
    total_membership_count = fields.Integer('Total Memberships', compute='_compute_membership_stats')
    active_subscription_count = fields.Integer('Active Subscriptions', compute='_compute_membership_stats')
    active_course_count = fields.Integer('Active Courses', compute='_compute_membership_stats')
    
    # Primary Membership (most recent active)
    primary_membership_id = fields.Many2one('ams.membership.membership', 'Primary Membership',
                                          compute='_compute_primary_membership', store=True)
    
    # Membership History
    first_membership_date = fields.Date('First Membership Date', compute='_compute_membership_history', store=True)
    membership_tenure_years = fields.Float('Membership Tenure (Years)', compute='_compute_membership_history', store=True)
    total_renewals = fields.Integer('Total Renewals', compute='_compute_membership_history', store=True)
    
    # Financial Summary
    total_membership_value = fields.Float('Total Membership Value', compute='_compute_financial_stats')
    annual_subscription_value = fields.Float('Annual Subscription Value', compute='_compute_financial_stats')
    lifetime_donation_total = fields.Float('Lifetime Donation Total', compute='_compute_financial_stats')
    
    # Portal and Access
    has_active_subscriptions = fields.Boolean('Has Active Subscriptions', compute='_compute_access_status')
    digital_access_count = fields.Integer('Digital Access Count', compute='_compute_access_status')
    
    # Communication Preferences (extended from foundation)
    subscription_notifications = fields.Boolean('Subscription Notifications', default=True)
    course_notifications = fields.Boolean('Course Notifications', default=True)
    renewal_reminders = fields.Boolean('Renewal Reminders', default=True)

    @api.depends('membership_ids.state', 'chapter_membership_ids.state', 'subscription_ids.state', 'course_ids.state')
    def _compute_membership_stats(self):
        """Compute membership statistics"""
        for partner in self:
            # Active memberships
            partner.active_membership_count = len(partner.membership_ids.filtered(
                lambda m: m.state in ['active', 'grace']
            ))
            
            # Total memberships
            partner.total_membership_count = len(partner.membership_ids)
            
            # Active subscriptions
            partner.active_subscription_count = len(partner.subscription_ids.filtered(
                lambda s: s.state in ['active', 'grace']
            ))
            
            # Active courses
            partner.active_course_count = len(partner.course_ids.filtered(
                lambda c: c.state in ['active', 'grace']
            ))

    @api.depends('membership_ids.state', 'membership_ids.start_date')
    def _compute_primary_membership(self):
        """Compute primary (most recent active) membership"""
        for partner in self:
            active_memberships = partner.membership_ids.filtered(
                lambda m: m.state in ['active', 'grace']
            ).sorted('start_date', reverse=True)
            
            partner.primary_membership_id = active_memberships[0] if active_memberships else False

    @api.depends('membership_ids.start_date')
    def _compute_membership_history(self):
        """Compute membership history statistics"""
        for partner in self:
            all_memberships = partner.membership_ids.sorted('start_date')
            
            if all_memberships:
                partner.first_membership_date = all_memberships[0].start_date
                partner.total_renewals = len(all_memberships) - 1
                
                # Calculate tenure from first membership to now
                if partner.first_membership_date:
                    today = fields.Date.today()
                    years = (today - partner.first_membership_date).days / 365.25
                    partner.membership_tenure_years = round(years, 1)
                else:
                    partner.membership_tenure_years = 0.0
            else:
                partner.first_membership_date = False
                partner.total_renewals = 0
                partner.membership_tenure_years = 0.0

    def _compute_financial_stats(self):
        """Compute financial statistics"""
        for partner in self:
            # Total membership value (all time)
            membership_value = sum(partner.membership_ids.mapped('paid_amount'))
            partner.total_membership_value = membership_value
            
            # Annual subscription value (active subscriptions)
            active_subscriptions = partner.subscription_ids.filtered(
                lambda s: s.state in ['active', 'grace']
            )
            annual_sub_value = sum(sub.paid_amount for sub in active_subscriptions)
            partner.annual_subscription_value = annual_sub_value
            
            # Lifetime donation total
            donation_total = sum(partner.donation_ids.mapped('total_donated'))
            partner.lifetime_donation_total = donation_total

    def _compute_access_status(self):
        """Compute digital access and subscription status"""
        for partner in self:
            # Check for active subscriptions
            active_subs = partner.subscription_ids.filtered(
                lambda s: s.state in ['active', 'grace']
            )
            partner.has_active_subscriptions = len(active_subs) > 0
            
            # Count digital access subscriptions
            digital_access = active_subs.filtered('digital_access_granted')
            partner.digital_access_count = len(digital_access)

    # Action Methods
    def action_view_memberships(self):
        """View all membership records"""
        self.ensure_one()
        return {
            'name': _('Memberships: %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'ams.membership.membership',
            'view_mode': 'list,form',
            'domain': [('partner_id', '=', self.id)],
            'context': {
                'default_partner_id': self.id,
                'search_default_active': 1,
            },
        }

    def action_view_subscriptions(self):
        """View all subscription records"""
        self.ensure_one()
        return {
            'name': _('Subscriptions: %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'ams.membership.subscription',
            'view_mode': 'list,form',
            'domain': [('partner_id', '=', self.id)],
            'context': {
                'default_partner_id': self.id,
                'search_default_active': 1,
            },
        }

    def action_view_courses(self):
        """View all course records"""
        self.ensure_one()
        return {
            'name': _('Courses: %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'ams.membership.course',
            'view_mode': 'list,form',
            'domain': [('partner_id', '=', self.id)],
            'context': {
                'default_partner_id': self.id,
                'search_default_active': 1,
            },
        }

    def action_view_donations(self):
        """View all donation records"""
        self.ensure_one()
        return {
            'name': _('Donations: %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'ams.membership.donation',
            'view_mode': 'list,form',
            'domain': [('partner_id', '=', self.id)],
            'context': {
                'default_partner_id': self.id,
                'search_default_active': 1,
            },
        }

    def action_create_membership(self):
        """Create new membership"""
        self.ensure_one()
        
        # Check if member can have multiple active memberships
        settings = self.env['ams.settings'].search([('active', '=', True)], limit=1)
        if settings and not settings.allow_multiple_active_memberships:
            if self.active_membership_count > 0:
                raise UserError(_("Member already has an active membership. Multiple active memberships are not allowed."))
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Create Membership'),
            'res_model': 'ams.membership.membership',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_partner_id': self.id,
                'default_start_date': fields.Date.today(),
            }
        }

    def action_create_subscription(self):
        """Create new subscription"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Create Subscription'),
            'res_model': 'ams.membership.subscription',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_partner_id': self.id,
                'default_start_date': fields.Date.today(),
            }
        }

    def action_enroll_course(self):
        """Enroll in course"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Enroll in Course'),
            'res_model': 'ams.membership.course',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_partner_id': self.id,
                'default_enrollment_date': fields.Date.today(),
                'default_start_date': fields.Date.today(),
            }
        }

    def action_setup_donation(self):
        """Set up recurring donation"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Setup Donation'),
            'res_model': 'ams.membership.donation',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_partner_id': self.id,
                'default_start_date': fields.Date.today(),
            }
        }

    def action_membership_renewal_wizard(self):
        """Open membership renewal wizard"""
        self.ensure_one()
        
        # Find renewable memberships
        renewable_memberships = self.membership_ids.filtered(
            lambda m: m.can_be_renewed
        )
        
        if not renewable_memberships:
            raise UserError(_("No renewable memberships found."))
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Renew Memberships'),
            'res_model': 'ams.membership.renewal.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_partner_id': self.id,
                'renewable_membership_ids': renewable_memberships.ids,
            }
        }

    def action_membership_upgrade_wizard(self):
        """Open membership upgrade wizard"""
        self.ensure_one()
        
        # Find upgradeable memberships
        active_memberships = self.membership_ids.filtered(
            lambda m: m.state in ['active', 'grace']
        )
        
        if not active_memberships:
            raise UserError(_("No active memberships found for upgrade."))
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Upgrade Membership'),
            'res_model': 'ams.membership.upgrade.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_partner_id': self.id,
                'current_membership_ids': active_memberships.ids,
            }
        }

    def action_member_dashboard(self):
        """Open member dashboard"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url': f'/my/membership/dashboard',
            'target': 'self',
        }

    # Member-specific Methods
    def get_active_memberships_summary(self):
        """Get summary of active memberships"""
        self.ensure_one()
        
        summary = {
            'memberships': [],
            'subscriptions': [],
            'courses': [],
            'total_value': 0.0
        }
        
        # Active memberships
        for membership in self.membership_ids.filtered(lambda m: m.state in ['active', 'grace']):
            summary['memberships'].append({
                'name': membership.name,
                'type': membership.member_type_id.name if membership.member_type_id else '',
                'start_date': membership.start_date,
                'end_date': membership.end_date,
                'status': membership.state,
                'days_remaining': membership.days_remaining
            })
            summary['total_value'] += membership.paid_amount
        
        # Active subscriptions
        for subscription in self.subscription_ids.filtered(lambda s: s.state in ['active', 'grace']):
            summary['subscriptions'].append({
                'name': subscription.name,
                'type': subscription.subscription_type,
                'delivery_method': subscription.delivery_method,
                'end_date': subscription.end_date,
                'status': subscription.state
            })
            summary['total_value'] += subscription.paid_amount
        
        # Active courses
        for course in self.course_ids.filtered(lambda c: c.state in ['active', 'grace']):
            summary['courses'].append({
                'name': course.name,
                'type': course.course_type,
                'progress': course.progress_percentage,
                'status': course.completion_status,
                'access_expires': course.access_end_date
            })
            summary['total_value'] += course.paid_amount
        
        return summary

    def check_renewal_eligibility(self):
        """Check overall renewal eligibility"""
        self.ensure_one()
        
        renewable_items = []
        
        # Check memberships
        for membership in self.membership_ids:
            if membership.can_be_renewed:
                renewable_items.append({
                    'type': 'membership',
                    'record': membership,
                    'name': membership.name,
                    'expires': membership.end_date
                })
        
        # Check subscriptions
        for subscription in self.subscription_ids:
            if subscription.can_be_renewed:
                renewable_items.append({
                    'type': 'subscription', 
                    'record': subscription,
                    'name': subscription.name,
                    'expires': subscription.end_date
                })
        
        return renewable_items

    def get_member_benefits(self):
        """Get comprehensive list of member benefits"""
        self.ensure_one()
        
        all_benefits = set()
        
        # Membership benefits
        for membership in self.membership_ids.filtered(lambda m: m.state in ['active', 'grace']):
            benefits = membership.get_membership_benefits()
            all_benefits.update(benefits)
        
        # Chapter benefits
        for chapter in self.chapter_membership_ids.filtered(lambda c: c.state in ['active', 'grace']):
            benefits = chapter.get_chapter_benefits()
            all_benefits.update(benefits)
        
        # Subscription benefits
        for subscription in self.subscription_ids.filtered(lambda s: s.state in ['active', 'grace']):
            if subscription.digital_access_granted:
                all_benefits.add(_("Digital Content Access"))
            if subscription.archive_access_years > 0:
                all_benefits.add(_("Archive Access (%d years)") % subscription.archive_access_years)
        
        # Donation benefits (if any)
        for donation in self.donation_ids.filtered(lambda d: d.state in ['active', 'grace']):
            benefits = donation.get_donor_benefits()
            all_benefits.update(benefits)
        
        return sorted(list(all_benefits))

    def calculate_member_engagement_score(self):
        """Calculate comprehensive member engagement score"""
        self.ensure_one()
        
        total_score = 0.0
        
        # Base engagement from ams_foundation
        total_score += self.engagement_score or 0.0
        
        # Subscription engagement
        for subscription in self.subscription_ids.filtered(lambda s: s.state in ['active', 'grace']):
            total_score += subscription.engagement_score * 0.3  # Weight subscription engagement
        
        # Course completion rate
        completed_courses = self.course_ids.filtered(lambda c: c.completion_status == 'completed')
        total_courses = len(self.course_ids)
        if total_courses > 0:
            completion_rate = len(completed_courses) / total_courses
            total_score += completion_rate * 50  # Up to 50 points for course completion
        
        # Donation consistency (simplified)
        active_donations = len(self.donation_ids.filtered(lambda d: d.state in ['active', 'grace']))
        total_score += active_donations * 10  # 10 points per active donation
        
        # Membership tenure bonus
        if self.membership_tenure_years > 0:
            tenure_bonus = min(self.membership_tenure_years * 2, 20)  # Up to 20 points, 2 per year
            total_score += tenure_bonus
        
        return min(total_score, 100.0)  # Cap at 100

    # Portal Methods
    def _get_membership_portal_content(self):
        """Get content for member portal"""
        self.ensure_one()
        
        content = {
            'member_info': {
                'member_number': self.member_number,
                'member_status': self.member_status,
                'member_type': self.member_type_id.name if self.member_type_id else '',
                'tenure_years': self.membership_tenure_years,
            },
            'active_items': self.get_active_memberships_summary(),
            'benefits': self.get_member_benefits(),
            'engagement_score': self.calculate_member_engagement_score(),
            'renewal_eligible': self.check_renewal_eligibility(),
        }
        
        return content

    # Constraints
    @api.constrains('subscription_notifications', 'course_notifications', 'renewal_reminders')
    def _check_notification_preferences(self):
        """Validate notification preferences"""
        for partner in self:
            if partner.is_member:
                # Could add validation rules for required notifications
                pass

    def copy(self, default=None):
        """Override copy to handle membership relationships"""
        if default is None:
            default = {}
        
        # Don't copy membership records
        default.update({
            'membership_ids': [],
            'chapter_membership_ids': [],
            'subscription_ids': [],
            'course_ids': [],
            'donation_ids': [],
        })
        
        return super().copy(default)