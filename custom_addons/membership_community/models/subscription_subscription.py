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
    - Seat management (parent/child, allocation) = subscription_management
    - Membership-specific fields and classification = membership_community
    - Email notifications = membership_community overrides
    
    This keeps the model lean by inheriting all lifecycle and seat compute methods
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
    # NOTE: SEAT MANAGEMENT FIELDS INHERITED FROM BASE
    # The following fields are defined in subscription_management:
    # - parent_subscription_id, child_subscription_ids, is_seat_subscription
    # - seat_holder_id, max_seats, allocated_seat_count, available_seat_count
    # - seat_utilization
    # - _compute_is_seat_subscription(), _compute_seat_counts(), _compute_seat_utilization()
    # ==========================================

    # ==========================================
    # PRIMARY MEMBERSHIP RELATIONSHIPS (NEW - for chapters)
    # ==========================================
    
    related_subscription_ids = fields.Many2many(
        'subscription.subscription',
        'subscription_relation_rel',
        'subscription_id',
        'related_subscription_id',
        string='Related Subscriptions',
        help='Other subscriptions this member has (e.g., national + chapter)'
    )
    
    primary_subscription_id = fields.Many2one(
        'subscription.subscription',
        string='Primary Subscription',
        help='Primary/parent subscription required for this membership (e.g., national membership for chapter)',
        index=True
    )
    
    primary_subscription_valid = fields.Boolean(
        string='Primary Subscription Valid',
        compute='_compute_primary_subscription_valid',
        store=True,
        help='Primary subscription is active and valid'
    )
    
    requires_primary_membership = fields.Boolean(
        string='Requires Primary Membership',
        compute='_compute_requires_primary_membership',
        store=True,
        help='This subscription requires a primary/parent membership'
    )

    # ==========================================
    # COMPUTE METHODS - PRIMARY MEMBERSHIP (NEW)
    # ==========================================
    
    @api.depends('membership_category_id', 'membership_category_id.is_parent_required')
    def _compute_requires_primary_membership(self):
        """Determine if this subscription requires a primary membership"""
        for sub in self:
            sub.requires_primary_membership = (
                sub.membership_category_id and 
                sub.membership_category_id.is_parent_required
            )
    
    @api.depends('primary_subscription_id', 'primary_subscription_id.state')
    def _compute_primary_subscription_valid(self):
        """Check if primary subscription is active and valid"""
        for sub in self:
            if sub.primary_subscription_id:
                sub.primary_subscription_valid = (
                    sub.primary_subscription_id.state in ('active', 'trial')
                )
            else:
                # If no primary required, consider it valid
                sub.primary_subscription_valid = not sub.requires_primary_membership

    # ==========================================
    # PRIMARY MEMBERSHIP VALIDATION HOOKS (NEW)
    # Extension points for specialized modules
    # ==========================================
    
    def _check_primary_membership_requirement(self):
        """
        Hook for specialized modules to validate primary membership requirements
        Override in membership_chapter to enforce national membership
        
        Returns:
            tuple: (bool: is_valid, str: error_message)
        """
        self.ensure_one()
        
        # Base implementation: check if primary subscription exists and is valid
        if self.requires_primary_membership:
            if not self.primary_subscription_id:
                return (False, _('This membership requires a primary membership.'))
            
            if not self.primary_subscription_valid:
                return (False, _('Primary membership is not active.'))
        
        return (True, '')
    
    def _get_required_primary_categories(self):
        """
        Get list of membership categories that can serve as primary membership
        Override in membership_chapter to return national membership categories
        
        Returns:
            recordset: membership.category records that are valid primaries
        """
        if self.membership_category_id and self.membership_category_id.parent_category_id:
            return self.membership_category_id.parent_category_id
        return self.env['membership.category']
    
    def _get_valid_primary_subscriptions(self):
        """
        Get list of valid primary subscriptions for this member
        Override in specialized modules to add custom filtering
        
        Returns:
            recordset: subscription.subscription records that can be primaries
        """
        self.ensure_one()
        
        required_categories = self._get_required_primary_categories()
        if not required_categories:
            return self.env['subscription.subscription']
        
        return self.env['subscription.subscription'].search([
            ('partner_id', '=', self.partner_id.id),
            ('membership_category_id', 'in', required_categories.ids),
            ('state', 'in', ('active', 'trial')),
        ])
    
    def _auto_assign_primary_subscription(self):
        """
        Automatically assign primary subscription if one is available
        Override in specialized modules to customize assignment logic
        
        Returns:
            bool: True if primary was assigned, False otherwise
        """
        self.ensure_one()
        
        if not self.requires_primary_membership:
            return False
        
        if self.primary_subscription_id:
            return True  # Already has primary
        
        valid_primaries = self._get_valid_primary_subscriptions()
        if valid_primaries:
            self.primary_subscription_id = valid_primaries[0]
            _logger.info(f"Auto-assigned primary subscription {valid_primaries[0].name} to {self.name}")
            return True
        
        return False

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
        
        subscriptions = super().create(vals_list)
        
        # Auto-assign primary subscriptions if needed
        for subscription in subscriptions:
            if subscription.requires_primary_membership:
                subscription._auto_assign_primary_subscription()
        
        return subscriptions

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
                
                # Try to auto-assign primary if needed
                if subscription.requires_primary_membership and not subscription.primary_subscription_id:
                    subscription._auto_assign_primary_subscription()
        
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
                # Check primary membership requirement
                is_valid, error_msg = subscription._check_primary_membership_requirement()
                if not is_valid:
                    raise UserError(error_msg)
                
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

    def action_activate(self):
        """Override to handle membership activation"""
        # Pre-activation checks for memberships
        for subscription in self:
            if subscription.is_membership:
                # Check primary membership requirement before activation
                is_valid, error_msg = subscription._check_primary_membership_requirement()
                if not is_valid:
                    raise UserError(_('Cannot activate subscription: %s') % error_msg)
        
        # Call parent activation
        result = super().action_activate()
        
        # Post-activation membership tasks
        for subscription in self:
            if subscription.is_membership and subscription.state == 'active':
                # Assign member number
                if not subscription.partner_id.member_number:
                    subscription.partner_id.member_number = self.env['ir.sequence'].next_by_code('member.number')
                    _logger.info(f"Assigned member number {subscription.partner_id.member_number} to {subscription.partner_id.name}")
                
                # Set join date
                if not subscription.join_date:
                    subscription.join_date = subscription.date_start or fields.Date.today()
                
                # Send welcome email
                subscription._send_membership_welcome_email()
        
        return result

    def action_start_trial(self):
        """Override to handle trial start for memberships"""
        # Pre-trial checks for memberships
        for subscription in self:
            if subscription.is_membership:
                # Check primary membership requirement before trial
                is_valid, error_msg = subscription._check_primary_membership_requirement()
                if not is_valid:
                    raise UserError(_('Cannot start trial: %s') % error_msg)
        
        # Call parent trial start
        result = super().action_start_trial()
        
        # Post-trial membership tasks
        for subscription in self:
            if subscription.is_membership and subscription.state == 'trial':
                # Assign member number
                if not subscription.partner_id.member_number:
                    subscription.partner_id.member_number = self.env['ir.sequence'].next_by_code('member.number')
                    _logger.info(f"Assigned member number {subscription.partner_id.member_number} to {subscription.partner_id.name}")
                
                # Set join date
                if not subscription.join_date:
                    subscription.join_date = subscription.date_start or fields.Date.today()
                
                # Send welcome email  
                subscription._send_membership_welcome_email()
        
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
    
    def action_view_primary_subscription(self):
        """View the primary subscription"""
        self.ensure_one()
        
        if not self.primary_subscription_id:
            raise UserError(_("This subscription does not have a primary subscription"))
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Primary Subscription: %s') % self.primary_subscription_id.name,
            'res_model': 'subscription.subscription',
            'view_mode': 'form',
            'res_id': self.primary_subscription_id.id,
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
    
    @api.constrains('primary_subscription_id', 'partner_id')
    def _check_primary_subscription_partner(self):
        """Ensure primary subscription belongs to same partner"""
        for subscription in self:
            if subscription.primary_subscription_id:
                if subscription.primary_subscription_id.partner_id != subscription.partner_id:
                    raise ValidationError(_(
                        "Primary subscription must belong to the same partner"
                    ))