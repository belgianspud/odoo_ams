# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import timedelta
import logging

_logger = logging.getLogger(__name__)

class SubscriptionSubscription(models.Model):
    """
    Simplified Subscription Extensions for Base Membership Module
    Extends subscription_management module with minimal membership fields
    """
    _inherit = 'subscription.subscription'

    # ==========================================
    # CORE MEMBERSHIP FIELDS ONLY
    # ==========================================
    
    membership_category_id = fields.Many2one(
        'membership.category',
        string='Member Category',
        help='Category assigned to this membership',
        tracking=True
    )
    
    # ==========================================
    # PRODUCT HELPER FIELDS
    # Quick access to check if this is a membership subscription
    # ==========================================
    
    is_membership = fields.Boolean(
        string='Is Membership',
        related='plan_id.product_template_id.is_membership_product',
        store=True,
        help='This subscription is a membership'
    )
    
    subscription_product_type = fields.Selection(
        related='plan_id.product_template_id.subscription_product_type',
        string='Subscription Type',
        store=True
    )

    # ==========================================
    # BASIC ELIGIBILITY - Core only
    # Specialized modules extend this
    # ==========================================
    
    eligibility_verified = fields.Boolean(
        string='Eligibility Verified',
        default=False,
        tracking=True,
        help='Membership eligibility has been verified'
    )
    
    eligibility_verified_by = fields.Many2one(
        'res.users',
        string='Verified By',
        help='User who verified eligibility'
    )
    
    eligibility_verified_date = fields.Date(
        string='Verification Date',
        help='Date when eligibility was verified'
    )

    # ==========================================
    # MEMBERSHIP SOURCE
    # How this membership was created
    # ==========================================
    
    source_type = fields.Selection(
        selection='_get_source_types',
        string='Source Type',
        default='direct',
        tracking=True,
        help='How this membership was created'
    )
    
    @api.model
    def _get_source_types(self):
        """Base source types - can be extended by specialized modules"""
        return [
            ('direct', 'Direct Signup'),
            ('renewal', 'Renewal'),
            ('import', 'Data Import'),
            ('admin', 'Admin Created'),
        ]
    
    join_date = fields.Date(
        string='Original Join Date',
        help='Date when member first joined',
        tracking=True
    )


    # ==========================================
    # GRACE PERIOD & LIFECYCLE FIELDS
    # ==========================================
    
    # Period Overrides (can be customized per subscription)
    grace_period_days = fields.Integer(
        string='Grace Period (Days)',
        default=lambda self: int(self.env['ir.config_parameter'].sudo().get_param(
            'membership.grace_period_days', '30')),
        help='Days after expiry before suspension'
    )
    
    suspend_period_days = fields.Integer(
        string='Suspension Period (Days)',
        default=lambda self: int(self.env['ir.config_parameter'].sudo().get_param(
            'membership.suspend_period_days', '60')),
        help='Days in suspension before termination'
    )
    
    terminate_period_days = fields.Integer(
        string='Termination Period (Days)',
        default=lambda self: int(self.env['ir.config_parameter'].sudo().get_param(
            'membership.terminate_period_days', '90')),
        help='Total days before termination'
    )
    
    # Computed Dates
    paid_through_date = fields.Date(
        string='Paid Through Date',
        compute='_compute_paid_through_date',
        store=True,
        help='Last date member has paid for (same as date_end for active memberships)'
    )
    
    grace_period_end_date = fields.Date(
        string='Grace Period End Date',
        compute='_compute_lifecycle_dates',
        store=True,
        help='Date when grace period ends and suspension begins'
    )
    
    suspend_end_date = fields.Date(
        string='Suspension End Date',
        compute='_compute_lifecycle_dates',
        store=True,
        help='Date when suspension ends and termination occurs'
    )
    
    terminate_date = fields.Date(
        string='Termination Date',
        compute='_compute_lifecycle_dates',
        store=True,
        help='Final termination date'
    )
    
    # Status Flags
    is_in_grace_period = fields.Boolean(
        string='In Grace Period',
        compute='_compute_lifecycle_status',
        store=True,
        help='Member is past expiry but within grace period'
    )
    
    is_pending_suspension = fields.Boolean(
        string='Pending Suspension',
        compute='_compute_lifecycle_status',
        store=True,
        help='Grace period has ended, suspension is pending'
    )
    
    is_pending_termination = fields.Boolean(
        string='Pending Termination',
        compute='_compute_lifecycle_status',
        store=True,
        help='Suspension period has ended, termination is pending'
    )
    
    lifecycle_stage = fields.Selection([
        ('active', 'Active'),
        ('grace', 'Grace Period'),
        ('suspended', 'Suspended'),
        ('terminated', 'Terminated'),
    ], string='Lifecycle Stage',
       compute='_compute_lifecycle_status',
       store=True,
       help='Current stage in membership lifecycle')
    
    days_in_grace = fields.Integer(
        string='Days in Grace',
        compute='_compute_lifecycle_status',
        help='Number of days currently in grace period'
    )
    
    days_until_suspension = fields.Integer(
        string='Days Until Suspension',
        compute='_compute_lifecycle_status',
        help='Days remaining before suspension'
    )
    
    days_until_termination = fields.Integer(
        string='Days Until Termination',
        compute='_compute_lifecycle_status',
        help='Days remaining before termination'
    )
    
    # Tracking
    grace_period_start_date = fields.Date(
        string='Grace Period Started',
        readonly=True,
        tracking=True,
        help='Date when member entered grace period'
    )
    
    actual_suspend_date = fields.Date(
        string='Actually Suspended On',
        readonly=True,
        tracking=True,
        help='Date when member was actually suspended'
    )
    
    actual_terminate_date = fields.Date(
        string='Actually Terminated On',
        readonly=True,
        tracking=True,
        help='Date when member was actually terminated'
    )
    
    # Email Tracking
    last_grace_email_date = fields.Date(
        string='Last Grace Email',
        help='Last date grace period email was sent'
    )
    # ==========================================
    # CRUD OVERRIDES - Minimal
    # ==========================================

    @api.model_create_multi
    def create(self, vals_list):
        """Set membership defaults on create"""
        
        for vals in vals_list:
            plan_id = vals.get('plan_id')
            if plan_id:
                plan = self.env['subscription.plan'].browse(plan_id)
                product = plan.product_template_id
                
                # Only process if membership product
                if product.is_membership_product:
                    # Set join_date if not provided
                    if 'join_date' not in vals:
                        vals['join_date'] = vals.get('date_start', fields.Date.today())
                    
                    # Set default category from product if not provided
                    if 'membership_category_id' not in vals:
                        if product.default_member_category_id:
                            vals['membership_category_id'] = product.default_member_category_id.id
        
        return super().create(vals_list)

    def write(self, vals):
        """Override to handle membership activation"""
        result = super().write(vals)
        
        # Auto-activate membership subscriptions when they move to active state
        for subscription in self:
            if subscription.is_membership and subscription.state == 'active':
                # Assign member number if not already assigned
                if not subscription.partner_id.member_number:
                    subscription.partner_id.member_number = self.env['ir.sequence'].next_by_code('member.number')
                
                # Set join date if not set
                if not subscription.join_date and 'join_date' not in vals:
                    subscription.join_date = subscription.date_start or fields.Date.today()
        
        return result

    # ==========================================
    # BUSINESS METHODS - Basic only
    # ==========================================

    def get_available_benefits(self):
        """Get benefits for this membership subscription"""
        self.ensure_one()
        if self.is_membership:
            return self.plan_id.product_template_id.benefit_ids
        return self.env['membership.benefit']

    def get_available_features(self):
        """Get features for this membership subscription"""
        self.ensure_one()
        if self.is_membership:
            return self.plan_id.product_template_id.feature_ids
        return self.env['membership.feature']

    def action_verify_eligibility(self):
        """Mark eligibility as verified"""
        for subscription in self:
            if subscription.is_membership:
                subscription.write({
                    'eligibility_verified': True,
                    'eligibility_verified_by': self.env.user.id,
                    'eligibility_verified_date': fields.Date.today(),
                })
        return True

    def action_confirm(self):
        """Confirm subscription and activate if membership"""
        result = super().action_confirm()
        
        for subscription in self:
            if subscription.is_membership:
                # Assign member number
                if not subscription.partner_id.member_number:
                    subscription.partner_id.member_number = self.env['ir.sequence'].next_by_code('member.number')
                
                # Set join date
                if not subscription.join_date:
                    subscription.join_date = subscription.date_start or fields.Date.today()
        
        return result

    # ==========================================
    # CONSTRAINTS - Basic validation only
    # Specialized modules add their own constraints
    # ==========================================

    @api.constrains('membership_category_id', 'plan_id')
    def _check_category_product_compatibility(self):
        """Basic check that category is compatible with product"""
        for subscription in self:
            if not subscription.is_membership:
                continue
                
            if not subscription.membership_category_id:
                continue
            
            # Basic validation - specialized modules add stricter checks
            product = subscription.plan_id.product_template_id
            
            # Check if product has a default category and it matches
            if product.default_member_category_id:
                if subscription.membership_category_id.category_type != product.default_member_category_id.category_type:
                    # Just a warning - specialized modules can enforce stricter rules
                    pass


    # ==========================================
    # COMPUTE METHODS
    # ==========================================
    
    @api.depends('date_end', 'last_invoice_date')
    def _compute_paid_through_date(self):
        """Calculate the date member is paid through"""
        for subscription in self:
            if subscription.state in ('active', 'trial'):
                subscription.paid_through_date = subscription.date_end
            else:
                subscription.paid_through_date = False
    
    @api.depends('paid_through_date', 'grace_period_days', 'suspend_period_days', 
                 'terminate_period_days', 'state')
    def _compute_lifecycle_dates(self):
        """Calculate grace, suspend, and terminate dates"""
        for subscription in self:
            if subscription.paid_through_date and subscription.is_membership:
                base_date = subscription.paid_through_date
                
                # Grace period end date
                subscription.grace_period_end_date = base_date + timedelta(
                    days=subscription.grace_period_days
                )
                
                # Suspend end date (grace + suspend period)
                subscription.suspend_end_date = base_date + timedelta(
                    days=subscription.grace_period_days + subscription.suspend_period_days
                )
                
                # Terminate date (grace + suspend + terminate period)
                # Note: terminate_period_days is the TOTAL, not additional
                subscription.terminate_date = base_date + timedelta(
                    days=subscription.terminate_period_days
                )
            else:
                subscription.grace_period_end_date = False
                subscription.suspend_end_date = False
                subscription.terminate_date = False
    
    @api.depends('paid_through_date', 'grace_period_end_date', 'suspend_end_date',
                 'terminate_date', 'state')
    def _compute_lifecycle_status(self):
        """Determine current lifecycle status"""
        today = fields.Date.today()
        
        for subscription in self:
            if not subscription.paid_through_date or not subscription.is_membership:
                subscription.is_in_grace_period = False
                subscription.is_pending_suspension = False
                subscription.is_pending_termination = False
                subscription.lifecycle_stage = 'active' if subscription.state == 'active' else False
                subscription.days_in_grace = 0
                subscription.days_until_suspension = 0
                subscription.days_until_termination = 0
                continue
            
            paid_through = subscription.paid_through_date
            grace_end = subscription.grace_period_end_date
            suspend_end = subscription.suspend_end_date
            terminate = subscription.terminate_date
            
            # Determine lifecycle stage
            if subscription.state == 'active':
                if today <= paid_through:
                    # Still within paid period
                    subscription.lifecycle_stage = 'active'
                    subscription.is_in_grace_period = False
                    subscription.is_pending_suspension = False
                    subscription.is_pending_termination = False
                    subscription.days_in_grace = 0
                    subscription.days_until_suspension = (grace_end - today).days if grace_end else 0
                    subscription.days_until_termination = (terminate - today).days if terminate else 0
                    
                elif today <= grace_end:
                    # In grace period
                    subscription.lifecycle_stage = 'grace'
                    subscription.is_in_grace_period = True
                    subscription.is_pending_suspension = False
                    subscription.is_pending_termination = False
                    subscription.days_in_grace = (today - paid_through).days
                    subscription.days_until_suspension = (grace_end - today).days
                    subscription.days_until_termination = (terminate - today).days if terminate else 0
                    
                else:
                    # Past grace period, should be suspended
                    subscription.lifecycle_stage = 'grace'  # Still marked grace until cron runs
                    subscription.is_in_grace_period = False
                    subscription.is_pending_suspension = True
                    subscription.is_pending_termination = False
                    subscription.days_in_grace = subscription.grace_period_days
                    subscription.days_until_suspension = 0
                    subscription.days_until_termination = (terminate - today).days if terminate else 0
                    
            elif subscription.state == 'suspended':
                subscription.lifecycle_stage = 'suspended'
                subscription.is_in_grace_period = False
                subscription.is_pending_suspension = False
                
                if suspend_end and today > suspend_end:
                    subscription.is_pending_termination = True
                    subscription.days_until_termination = 0
                else:
                    subscription.is_pending_termination = False
                    subscription.days_until_termination = (terminate - today).days if terminate else 0
                    
                subscription.days_in_grace = 0
                subscription.days_until_suspension = 0
                
            elif subscription.state in ('cancelled', 'expired'):
                subscription.lifecycle_stage = 'terminated'
                subscription.is_in_grace_period = False
                subscription.is_pending_suspension = False
                subscription.is_pending_termination = False
                subscription.days_in_grace = 0
                subscription.days_until_suspension = 0
                subscription.days_until_termination = 0
                
            else:
                # Draft, trial, etc.
                subscription.lifecycle_stage = False
                subscription.is_in_grace_period = False
                subscription.is_pending_suspension = False
                subscription.is_pending_termination = False
                subscription.days_in_grace = 0
                subscription.days_until_suspension = 0
                subscription.days_until_termination = 0

    # ==========================================
    # BUSINESS METHODS
    # ==========================================
    
    def action_enter_grace_period(self):
        """Manually enter grace period (usually automatic)"""
        self.ensure_one()
        if self.state == 'active' and not self.is_in_grace_period:
            self.grace_period_start_date = fields.Date.today()
            self._send_grace_period_email()
            
            self.message_post(
                body=f"Entered grace period. Grace ends on {self.grace_period_end_date}",
                message_type='notification'
            )
    
    def action_suspend_from_grace(self):
        """Suspend subscription after grace period ends"""
        self.ensure_one()
        
        if self.state == 'active':
            self.actual_suspend_date = fields.Date.today()
            self.action_suspend()
            
            # Send suspension email
            send_email = self.env['ir.config_parameter'].sudo().get_param(
                'membership.suspend_send_email', 'True'
            )
            if send_email == 'True':
                self._send_suspension_email()
            
            self.message_post(
                body=f"Suspended after grace period ended. Suspension ends on {self.suspend_end_date}",
                message_type='notification'
            )
    
    def action_terminate_from_suspension(self):
        """Terminate subscription after suspension period ends"""
        self.ensure_one()
        
        if self.state == 'suspended':
            self.actual_terminate_date = fields.Date.today()
            self.state = 'expired'
            
            # Send termination email
            self._send_termination_email()
            
            self.message_post(
                body=f"Membership terminated after suspension period ended.",
                message_type='notification'
            )
    
    def _send_grace_period_email(self):
        """Send grace period notification email"""
        template = self.env.ref(
            'membership_community.email_template_grace_period',
            raise_if_not_found=False
        )
        if template:
            template.send_mail(self.id, force_send=False)
            self.last_grace_email_date = fields.Date.today()
    
    def _send_suspension_email(self):
        """Send suspension notification email"""
        template = self.env.ref(
            'membership_community.email_template_suspended_from_grace',
            raise_if_not_found=False
        )
        if template:
            template.send_mail(self.id, force_send=False)
    
    def _send_termination_email(self):
        """Send termination notification email"""
        template = self.env.ref(
            'membership_community.email_template_terminated',
            raise_if_not_found=False
        )
        if template:
            template.send_mail(self.id, force_send=False)

    # ==========================================
    # CRON METHODS
    # ==========================================
    
    @api.model
    def _cron_process_grace_periods(self):
        """Process subscriptions entering or in grace period"""
        today = fields.Date.today()
        
        # Find subscriptions that should enter grace period
        entering_grace = self.search([
            ('is_membership', '=', True),
            ('state', '=', 'active'),
            ('paid_through_date', '<', today),
            ('grace_period_start_date', '=', False),
            ('grace_period_end_date', '>=', today),
        ])
        
        for subscription in entering_grace:
            subscription.action_enter_grace_period()
        
        _logger.info(f"Processed {len(entering_grace)} subscriptions entering grace period")
        
        # Send reminders for subscriptions in grace period
        send_reminders = self.env['ir.config_parameter'].sudo().get_param(
            'membership.grace_send_email', 'True'
        )
        if send_reminders == 'True':
            self._send_grace_reminders()
    
    @api.model
    def _cron_process_suspensions(self):
        """Process subscriptions that should be suspended"""
        today = fields.Date.today()
        
        # Find subscriptions past grace period
        to_suspend = self.search([
            ('is_membership', '=', True),
            ('state', '=', 'active'),
            ('grace_period_end_date', '<', today),
            ('actual_suspend_date', '=', False),
        ])
        
        for subscription in to_suspend:
            subscription.action_suspend_from_grace()
        
        _logger.info(f"Suspended {len(to_suspend)} subscriptions after grace period")
    
    @api.model
    def _cron_process_terminations(self):
        """Process subscriptions that should be terminated"""
        today = fields.Date.today()
        
        # Find suspended subscriptions past suspension period
        to_terminate = self.search([
            ('is_membership', '=', True),
            ('state', '=', 'suspended'),
            ('suspend_end_date', '<', today),
            ('actual_terminate_date', '=', False),
        ])
        
        for subscription in to_terminate:
            subscription.action_terminate_from_suspension()
        
        _logger.info(f"Terminated {len(to_terminate)} subscriptions after suspension period")
    
    @api.model
    def _send_grace_reminders(self):
        """Send reminder emails to members in grace period"""
        today = fields.Date.today()
        frequency = self.env['ir.config_parameter'].sudo().get_param(
            'membership.grace_email_frequency', 'weekly'
        )
        
        # Determine which subscriptions need reminders
        domain = [
            ('is_membership', '=', True),
            ('is_in_grace_period', '=', True),
            ('state', '=', 'active'),
        ]
        
        if frequency == 'once':
            # Only send if never sent before
            domain.append(('last_grace_email_date', '=', False))
        elif frequency == 'weekly':
            # Send if last email was 7+ days ago
            domain.append('|')
            domain.append(('last_grace_email_date', '=', False))
            domain.append(('last_grace_email_date', '<=', today - timedelta(days=7)))
        elif frequency == 'daily':
            # Send daily
            domain.append('|')
            domain.append(('last_grace_email_date', '=', False))
            domain.append(('last_grace_email_date', '<', today))
        
        subscriptions = self.search(domain)
        
        template = self.env.ref(
            'membership_community.email_template_grace_reminder',
            raise_if_not_found=False
        )
        
        if template:
            for subscription in subscriptions:
                template.send_mail(subscription.id, force_send=False)
                subscription.last_grace_email_date = today
        
        _logger.info(f"Sent grace reminders to {len(subscriptions)} members")