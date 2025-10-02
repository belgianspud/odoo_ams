# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
import logging

_logger = logging.getLogger(__name__)


class SubscriptionSubscription(models.Model):
    """
    Simplified Subscription Extensions for Membership
    
    Key Philosophy:
    - Lifecycle management (grace, suspend, terminate) = subscription_management
    - Membership-specific fields and classification = membership_community
    - Email notifications = membership_community overrides
    
    This keeps the model lean by inheriting all lifecycle compute methods
    from subscription_management rather than duplicating them.
    """
    _inherit = 'subscription.subscription'

    # ==========================================
    # MEMBERSHIP-SPECIFIC FIELDS ONLY
    # ==========================================
    
    membership_category_id = fields.Many2one(
        'membership.category',
        string='Member Category',
        help='Category assigned to this membership',
        tracking=True
    )
    
    # ==========================================
    # HELPER FLAGS (Computed from product)
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
    
    supports_seats = fields.Boolean(
        string='Supports Seats',
        related='plan_id.supports_seats',
        store=True,
        help='This subscription plan supports multiple seats'
    )

    # ==========================================
    # ELIGIBILITY VERIFICATION - Basic
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
    # MEMBERSHIP SOURCE TRACKING
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
        """
        Base source types - extensible by other modules
        
        Extension pattern for specialized modules:
            @api.model
            def _get_source_types(self):
                types = super()._get_source_types()
                types.extend([
                    ('referral', 'Member Referral'),
                    ('event', 'Event Signup'),
                ])
                return types
        """
        return [
            ('direct', 'Direct Signup'),
            ('renewal', 'Renewal'),
            ('import', 'Data Import'),
            ('admin', 'Admin Created'),
        ]
    
    join_date = fields.Date(
        string='Original Join Date',
        help='Date when member first joined (not renewal date)',
        tracking=True
    )

    # ==========================================
    # ORGANIZATIONAL MEMBERSHIP - SEAT SUPPORT
    # ==========================================
    
    # Parent-Child Subscription Relationships (REQUIRED for org memberships)
    parent_subscription_id = fields.Many2one(
        'subscription.subscription',
        string='Parent Subscription',
        help='Parent organizational subscription (for seat subscriptions)',
        index=True,
        ondelete='cascade'
    )
    
    child_subscription_ids = fields.One2many(
        'subscription.subscription',
        'parent_subscription_id',
        string='Seat Subscriptions',
        help='Child seat subscriptions under this organizational subscription'
    )
    
    is_seat_subscription = fields.Boolean(
        string='Is Seat Subscription',
        compute='_compute_is_seat_subscription',
        store=True,
        help='This subscription is a seat under an organizational subscription'
    )
    
    seat_holder_id = fields.Many2one(
        'res.partner',
        string='Seat Holder',
        help='Individual using this seat (for seat subscriptions)',
        index=True
    )
    
    # Seat Allocation (REQUIRED for org memberships)
    max_seats = fields.Integer(
        string='Maximum Seats',
        help='Maximum number of seats allowed for this subscription',
        default=0
    )
    
    allocated_seat_count = fields.Integer(
        string='Allocated Seats',
        compute='_compute_seat_counts',
        store=True,
        help='Number of seats currently allocated'
    )
    
    available_seat_count = fields.Integer(
        string='Available Seats',
        compute='_compute_seat_counts',
        store=True,
        help='Number of seats still available'
    )
    
    seat_utilization = fields.Float(
        string='Seat Utilization %',
        compute='_compute_seat_utilization',
        help='Percentage of seats currently in use'
    )

    # ==========================================
    # COMPUTE METHODS - SEAT MANAGEMENT
    # ==========================================
    
    @api.depends('parent_subscription_id')
    def _compute_is_seat_subscription(self):
        """Determine if this is a seat subscription"""
        for sub in self:
            sub.is_seat_subscription = bool(sub.parent_subscription_id)
    
    @api.depends('child_subscription_ids', 'max_seats')
    def _compute_seat_counts(self):
        """Calculate allocated and available seat counts"""
        for sub in self:
            sub.allocated_seat_count = len(sub.child_subscription_ids)
            sub.available_seat_count = max(0, sub.max_seats - sub.allocated_seat_count)
    
    @api.depends('allocated_seat_count', 'max_seats')
    def _compute_seat_utilization(self):
        """Calculate seat utilization percentage"""
        for sub in self:
            if sub.max_seats > 0:
                sub.seat_utilization = (sub.allocated_seat_count / sub.max_seats) * 100
            else:
                sub.seat_utilization = 0.0

    # ==========================================
    # NOTE: Lifecycle fields are inherited from subscription_management
    # We do NOT redefine them here:
    # - grace_period_days, suspend_period_days, terminate_period_days
    # - paid_through_date, grace_period_end_date, suspend_end_date, terminate_date
    # - is_in_grace_period, lifecycle_stage
    # - days_until_suspension, days_until_termination
    # - _compute_lifecycle_periods(), _compute_lifecycle_dates(), _compute_lifecycle_status()
    #
    # All of these are handled by subscription_management!
    # ==========================================

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
                
                # Only process membership products
                if product.is_membership_product:
                    # Set join_date if not provided
                    if 'join_date' not in vals:
                        vals['join_date'] = vals.get('date_start', fields.Date.today())
                    
                    # Set default category from product if not provided
                    if 'membership_category_id' not in vals and product.default_member_category_id:
                        vals['membership_category_id'] = product.default_member_category_id.id
                    
                    # Set max_seats from plan if organizational subscription
                    if product.subscription_product_type == 'organizational_membership':
                        if 'max_seats' not in vals and plan.max_seats > 0:
                            vals['max_seats'] = plan.max_seats
        
        return super().create(vals_list)

    def write(self, vals):
        """Handle membership-specific updates"""
        result = super().write(vals)
        
        # Auto-assign member numbers and join dates when activating
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
    # BUSINESS METHODS - Membership Specific
    # ==========================================

    def get_available_benefits(self):
        """Get benefits for this membership"""
        self.ensure_one()
        if self.is_membership:
            return self.plan_id.product_template_id.benefit_ids
        return self.env['membership.benefit']

    def get_available_features(self):
        """Get features for this membership"""
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
                
                subscription.message_post(
                    body=_('Eligibility verified by %s') % self.env.user.name,
                    message_type='notification'
                )
        return True

    def action_confirm(self):
        """Override to handle membership activation"""
        result = super().action_confirm()
        
        for subscription in self:
            if subscription.is_membership:
                # Assign member number
                if not subscription.partner_id.member_number:
                    subscription.partner_id.member_number = self.env['ir.sequence'].next_by_code('member.number')
                    _logger.info(f"Assigned member number {subscription.partner_id.member_number} to {subscription.partner_id.name}")
                
                # Set join date
                if not subscription.join_date:
                    subscription.join_date = subscription.date_start or fields.Date.today()
                
                # Send welcome email if configured
                if subscription.state in ['trial', 'active']:
                    self._send_membership_welcome_email()
        
        return result

    def _send_membership_welcome_email(self):
        """Send membership welcome email"""
        send_welcome = self.env['ir.config_parameter'].sudo().get_param(
            'subscription.send_welcome_email', 'True'
        )
        if send_welcome == 'True':
            template = self.env.ref(
                'subscription_management.email_template_subscription_welcome',
                raise_if_not_found=False
            )
            if template:
                try:
                    template.send_mail(self.id, force_send=False)
                    _logger.info(f"Sent welcome email for membership {self.name}")
                except Exception as e:
                    _logger.error(f"Failed to send welcome email for {self.name}: {e}")

    # ==========================================
    # ORGANIZATIONAL MEMBERSHIP - SEAT METHODS
    # ==========================================
    
    def action_allocate_seat(self, employee_partner_id):
        """
        Allocate a seat to an employee
        
        Args:
            employee_partner_id: ID of the partner to assign the seat to
            
        Returns:
            subscription.subscription: The created seat subscription
        """
        self.ensure_one()
        
        if not self.plan_id.supports_seats:
            raise UserError(_("This subscription plan does not support multiple seats"))
        
        if self.available_seat_count <= 0:
            raise UserError(_(
                "No available seats. Maximum seats: %s, Allocated: %s"
            ) % (self.max_seats, self.allocated_seat_count))
        
        # Get employee
        employee = self.env['res.partner'].browse(employee_partner_id)
        
        # Check if employee already has a seat
        existing_seat = self.child_subscription_ids.filtered(
            lambda s: s.seat_holder_id == employee
        )
        if existing_seat:
            raise UserError(_(
                "%s already has a seat subscription (%s)"
            ) % (employee.name, existing_seat.name))
        
        # Create seat subscription
        seat_sub = self.env['subscription.subscription'].create({
            'partner_id': employee_partner_id,
            'plan_id': self.plan_id.id,
            'parent_subscription_id': self.id,
            'seat_holder_id': employee_partner_id,
            'membership_category_id': self.membership_category_id.id,
            'date_start': self.date_start,
            'date_end': self.date_end,
            'state': 'active' if self.state == 'active' else 'draft',
            'price': 0.0,  # Seat price is covered by parent
        })
        
        # Link employee to organization
        employee.write({
            'parent_organization_id': self.partner_id.id,
            'seat_subscription_id': seat_sub.id,
        })
        
        self.message_post(
            body=_("Seat allocated to %s") % employee.name,
            message_type='notification'
        )
        
        _logger.info(f"Allocated seat {seat_sub.name} to {employee.name} under {self.name}")
        
        return seat_sub
    
    def action_deallocate_seat(self, seat_subscription_id):
        """
        Deallocate a seat
        
        Args:
            seat_subscription_id: ID of the seat subscription to deallocate
            
        Returns:
            bool: True if successful
        """
        self.ensure_one()
        
        seat_sub = self.env['subscription.subscription'].browse(seat_subscription_id)
        
        if seat_sub.parent_subscription_id != self:
            raise UserError(_("This seat does not belong to this subscription"))
        
        employee_name = seat_sub.seat_holder_id.name if seat_sub.seat_holder_id else 'Unknown'
        
        # Remove seat holder link
        if seat_sub.seat_holder_id:
            seat_sub.seat_holder_id.write({
                'seat_subscription_id': False,
            })
        
        # Cancel seat subscription
        seat_sub.action_cancel()
        
        self.message_post(
            body=_("Seat deallocated from %s") % employee_name,
            message_type='notification'
        )
        
        _logger.info(f"Deallocated seat {seat_sub.name} from {employee_name}")
        
        return True
    
    def action_view_seats(self):
        """View all seat subscriptions for this organization"""
        self.ensure_one()
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Seat Subscriptions - %s') % self.name,
            'res_model': 'subscription.subscription',
            'view_mode': 'list,form',
            'domain': [('parent_subscription_id', '=', self.id)],
            'context': {
                'default_parent_subscription_id': self.id,
                'default_plan_id': self.plan_id.id,
            }
        }
    
    def action_view_seat_holder(self):
        """View the partner record for the seat holder"""
        self.ensure_one()
        
        if not self.seat_holder_id:
            raise UserError(_("This subscription does not have a seat holder assigned"))
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Seat Holder: %s') % self.seat_holder_id.name,
            'res_model': 'res.partner',
            'view_mode': 'form',
            'res_id': self.seat_holder_id.id,
            'target': 'current',
        }

    # ==========================================
    # LIFECYCLE SYNCHRONIZATION (Parent → Child)
    # ==========================================
    
    def action_suspend(self):
        """Suspend subscription and cascade to child seats"""
        result = super().action_suspend()
        
        # Suspend all child seat subscriptions
        if self.child_subscription_ids:
            for child in self.child_subscription_ids:
                if child.state in ['active', 'trial']:
                    child.write({'state': 'suspended'})
                    child.message_post(
                        body=_("Suspended due to parent organization suspension"),
                        message_type='notification'
                    )
            
            _logger.info(f"Suspended {len(self.child_subscription_ids)} child seats under {self.name}")
        
        return result
    
    def action_cancel(self):
        """Cancel subscription and cascade to child seats"""
        result = super().action_cancel()
        
        # Cancel all child seat subscriptions
        if self.child_subscription_ids:
            for child in self.child_subscription_ids:
                if child.state not in ['cancelled', 'expired']:
                    child.write({'state': 'cancelled'})
                    child.message_post(
                        body=_("Cancelled due to parent organization cancellation"),
                        message_type='notification'
                    )
            
            _logger.info(f"Cancelled {len(self.child_subscription_ids)} child seats under {self.name}")
        
        return result
    
    def action_activate(self):
        """Activate subscription and cascade to child seats"""
        result = super().action_activate()
        
        # Reactivate child seat subscriptions
        if self.child_subscription_ids:
            for child in self.child_subscription_ids.filtered(lambda s: s.state == 'suspended'):
                child.write({'state': 'active'})
                child.message_post(
                    body=_("Reactivated due to parent organization reactivation"),
                    message_type='notification'
                )
            
            _logger.info(f"Reactivated {len(self.child_subscription_ids)} child seats under {self.name}")
        
        return result

    # ==========================================
    # EMAIL TEMPLATE OVERRIDES
    # Override parent methods to use membership-specific templates
    # These methods are called by subscription_management cron jobs
    # ==========================================
    
    def _send_grace_period_email(self):
        """Send membership-specific grace period notification"""
        template = self.env.ref(
            'membership_community.email_template_grace_period',
            raise_if_not_found=False
        )
        if template:
            try:
                template.send_mail(self.id, force_send=False)
                self.last_grace_email_date = fields.Date.today()
                _logger.info(f"Sent grace period email for membership {self.name}")
            except Exception as e:
                _logger.error(f"Failed to send grace period email for {self.name}: {e}")
    
    def _send_suspension_email(self):
        """Send membership-specific suspension notification"""
        template = self.env.ref(
            'membership_community.email_template_suspended_from_grace',
            raise_if_not_found=False
        )
        if template:
            try:
                template.send_mail(self.id, force_send=False)
                _logger.info(f"Sent suspension email for membership {self.name}")
            except Exception as e:
                _logger.error(f"Failed to send suspension email for {self.name}: {e}")
    
    def _send_termination_email(self):
        """Send membership-specific termination notification"""
        template = self.env.ref(
            'membership_community.email_template_terminated',
            raise_if_not_found=False
        )
        if template:
            try:
                template.send_mail(self.id, force_send=False)
                _logger.info(f"Sent termination email for membership {self.name}")
            except Exception as e:
                _logger.error(f"Failed to send termination email for {self.name}: {e}")

    # ==========================================
    # CONSTRAINTS - Basic validation
    # ==========================================

    @api.constrains('membership_category_id', 'plan_id')
    def _check_category_product_compatibility(self):
        """
        Basic validation - check category type matches product type
        
        This is a soft validation - just logs a warning rather than blocking.
        Specialized modules can add stricter validations.
        """
        for subscription in self:
            if not subscription.is_membership:
                continue
                
            if not subscription.membership_category_id:
                continue
            
            product = subscription.plan_id.product_template_id
            
            # Check type compatibility
            if product.default_member_category_id:
                if subscription.membership_category_id.category_type != product.default_member_category_id.category_type:
                    # Just a warning in chatter, don't block
                    subscription.message_post(
                        body=_("⚠️ Warning: Category type '%s' doesn't match product's default category type '%s'") % (
                            subscription.membership_category_id.category_type,
                            product.default_member_category_id.category_type
                        ),
                        message_type='notification'
                    )
    
    @api.constrains('parent_subscription_id', 'seat_holder_id')
    def _check_seat_subscription_integrity(self):
        """Validate seat subscription setup"""
        for subscription in self:
            # If this is a seat subscription, it must have a seat holder
            if subscription.parent_subscription_id and not subscription.seat_holder_id:
                raise ValidationError(_(
                    "Seat subscriptions must have a seat holder assigned"
                ))
            
            # Cannot have both parent and children
            if subscription.parent_subscription_id and subscription.child_subscription_ids:
                raise ValidationError(_(
                    "A subscription cannot be both a parent and a child (seat)"
                ))
    
    @api.constrains('max_seats', 'child_subscription_ids')
    def _check_seat_allocation_limit(self):
        """Ensure we don't exceed max seats"""
        for subscription in self:
            if subscription.max_seats > 0:
                if len(subscription.child_subscription_ids) > subscription.max_seats:
                    raise ValidationError(_(
                        "Cannot allocate more than %s seats. Currently allocated: %s"
                    ) % (subscription.max_seats, len(subscription.child_subscription_ids)))