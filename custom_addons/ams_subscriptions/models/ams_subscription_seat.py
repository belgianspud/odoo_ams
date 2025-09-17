# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import date, timedelta
import logging

_logger = logging.getLogger(__name__)


class AMSSubscriptionSeat(models.Model):
    """
    Enhanced AMS Subscription Seat Model - Layer 2 Architecture
    
    Manages individual seat assignments for enterprise subscriptions.
    
    Layer 2 Responsibilities:
    - Seat assignment and lifecycle management
    - Integration with contact management
    - Usage tracking and reporting
    - Portal access management for seat holders
    - Seat transfer and reassignment workflows
    """
    _name = 'ams.subscription.seat'
    _description = 'AMS Subscription Seat - Enhanced'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'subscription_id, assigned_date desc, contact_id'

    # ========================================================================
    # CORE SEAT FIELDS
    # ========================================================================
    
    subscription_id = fields.Many2one(
        'ams.subscription',
        string='Subscription',
        required=True,
        ondelete='cascade',
        index=True,
        help='The enterprise subscription this seat belongs to'
    )
    
    contact_id = fields.Many2one(
        'res.partner',
        string='Assigned Contact',
        required=True,
        tracking=True,
        domain=[('is_company', '=', False)],
        help='The individual contact assigned to this seat'
    )
    
    # Subscription context (computed from subscription for easy access)
    account_id = fields.Many2one(
        'res.partner',
        string='Account',
        related='subscription_id.account_id',
        store=True,
        help='The company/account that owns the subscription'
    )
    
    subscription_name = fields.Char(
        string='Subscription',
        related='subscription_id.name',
        store=True,
        help='Name of the parent subscription'
    )
    
    subscription_state = fields.Selection(
        related='subscription_id.state',
        string='Subscription Status',
        store=True,
        help='Current status of the parent subscription'
    )

    # ========================================================================
    # SEAT ASSIGNMENT DETAILS
    # ========================================================================
    
    assigned_date = fields.Date(
        string='Assigned Date',
        default=fields.Date.context_today,
        required=True,
        tracking=True,
        help='Date when this seat was assigned to the contact'
    )
    
    assigned_by_user_id = fields.Many2one(
        'res.users',
        string='Assigned By',
        default=lambda self: self.env.user,
        tracking=True,
        help='User who assigned this seat'
    )
    
    active = fields.Boolean(
        string='Active Seat',
        default=True,
        tracking=True,
        help='When unchecked, the seat is freed for reassignment'
    )
    
    # Deactivation tracking
    deactivated_date = fields.Date(
        string='Deactivated Date',
        tracking=True,
        help='Date when this seat was deactivated'
    )
    
    deactivated_by_user_id = fields.Many2one(
        'res.users',
        string='Deactivated By',
        tracking=True,
        help='User who deactivated this seat'
    )
    
    deactivation_reason = fields.Selection([
        ('employee_left', 'Employee Left Company'),
        ('no_longer_needed', 'No Longer Needed'),
        ('reassignment', 'Reassigned to Someone Else'),
        ('subscription_change', 'Subscription Changed'),
        ('admin_request', 'Administrative Request'),
        ('other', 'Other'),
    ], string='Deactivation Reason',
       tracking=True,
       help='Reason why this seat was deactivated')
    
    deactivation_notes = fields.Text(
        string='Deactivation Notes',
        help='Additional notes about the deactivation'
    )

    # ========================================================================
    # SEAT UTILIZATION AND TRACKING
    # ========================================================================
    
    last_access_date = fields.Datetime(
        string='Last Access',
        help='Last time this contact accessed member resources (if tracked)'
    )
    
    access_count = fields.Integer(
        string='Access Count',
        default=0,
        help='Number of times this contact has accessed member resources'
    )
    
    portal_user_id = fields.Many2one(
        'res.users',
        string='Portal User',
        help='Portal user account for this seat holder'
    )
    
    has_portal_access = fields.Boolean(
        string='Has Portal Access',
        compute='_compute_has_portal_access',
        store=True,
        help='Whether this seat holder has portal access'
    )

    # ========================================================================
    # SEAT PERMISSIONS AND ROLES
    # ========================================================================
    
    seat_role = fields.Selection([
        ('standard', 'Standard User'),
        ('admin', 'Account Administrator'),
        ('manager', 'Department Manager'),
        ('readonly', 'Read-Only Access'),
    ], string='Seat Role',
       default='standard',
       tracking=True,
       help='Role/permissions level for this seat')
    
    can_manage_seats = fields.Boolean(
        string='Can Manage Other Seats',
        default=False,
        help='Allow this seat holder to assign/remove other seats'
    )
    
    department = fields.Char(
        string='Department',
        help='Department or division of the seat holder'
    )
    
    job_title = fields.Char(
        string='Job Title',
        help='Job title of the seat holder'
    )

    # ========================================================================
    # INTEGRATION FIELDS (Layer 2 integration)
    # ========================================================================
    
    # Integration with ams_products_base for member benefits
    member_benefits_granted = fields.Many2many(
        'product.template',
        'seat_benefit_rel',
        'seat_id',
        'product_id',
        string='Benefits Granted',
        domain=[('is_ams_product', '=', True)],
        help='Benefits specifically granted to this seat holder'
    )
    
    # Portal groups granted (inherits from subscription/tier)
    portal_group_ids = fields.Many2many(
        'res.groups',
        'seat_portal_group_rel',
        'seat_id',
        'group_id',
        string='Portal Groups',
        help='Portal groups granted to this seat holder'
    )

    # ========================================================================
    # COMPUTED FIELDS
    # ========================================================================
    
    @api.depends('portal_user_id', 'portal_user_id.active')
    def _compute_has_portal_access(self):
        """Check if seat holder has active portal access"""
        for seat in self:
            seat.has_portal_access = bool(
                seat.portal_user_id and 
                seat.portal_user_id.active and 
                seat.portal_user_id.has_group('base.group_portal')
            )
    
    @api.depends('assigned_date', 'deactivated_date', 'active')
    def _compute_seat_duration(self):
        """Calculate how long this seat has been active"""
        for seat in self:
            if seat.assigned_date:
                end_date = seat.deactivated_date or fields.Date.today()
                seat.seat_duration_days = (end_date - seat.assigned_date).days
            else:
                seat.seat_duration_days = 0
    
    seat_duration_days = fields.Integer(
        string='Seat Duration (Days)',
        compute='_compute_seat_duration',
        store=True,
        help='Number of days this seat has been assigned'
    )

    # ========================================================================
    # ONCHANGE METHODS
    # ========================================================================
    
    @api.onchange('subscription_id')
    def _onchange_subscription_id(self):
        """Set defaults and domain based on subscription"""
        if self.subscription_id:
            # Set domain for contact_id based on account
            account = self.subscription_id.account_id
            if account:
                # Limit to contacts under the account company
                return {
                    'domain': {
                        'contact_id': [
                            '|',
                            ('parent_id', '=', account.id),
                            ('id', '=', account.id)
                        ]
                    }
                }
    
    @api.onchange('contact_id')
    def _onchange_contact_id(self):
        """Auto-populate fields from contact"""
        if self.contact_id:
            self.department = self.contact_id.category_id.name if self.contact_id.category_id else ''
            self.job_title = self.contact_id.function or ''
    
    @api.onchange('active')
    def _onchange_active(self):
        """Handle seat activation/deactivation"""
        if not self.active and not self.deactivated_date:
            self.deactivated_date = fields.Date.today()
            self.deactivated_by_user_id = self.env.user.id
        elif self.active and self.deactivated_date:
            # Reactivating seat
            self.deactivated_date = False
            self.deactivated_by_user_id = False
            self.deactivation_reason = False
            self.deactivation_notes = False

    # ========================================================================
    # CONSTRAINT VALIDATION
    # ========================================================================
    
    @api.constrains('subscription_id', 'contact_id')
    def _check_seat_limits(self):
        """Ensure subscription has enough seats available"""
        for seat in self:
            if seat.active and seat.subscription_id:
                subscription = seat.subscription_id
                active_seats = subscription.seat_ids.filtered('active')
                
                if len(active_seats) > subscription.total_seats:
                    raise ValidationError(_(
                        f"Cannot assign more seats than available. "
                        f"Subscription '{subscription.name}' has {subscription.total_seats} seats, "
                        f"but {len(active_seats)} are assigned."
                    ))
    
    @api.constrains('subscription_id', 'contact_id', 'active')
    def _check_duplicate_assignment(self):
        """Prevent same contact being assigned multiple active seats in same subscription"""
        for seat in self:
            if seat.active and seat.subscription_id and seat.contact_id:
                duplicate_seats = self.search([
                    ('subscription_id', '=', seat.subscription_id.id),
                    ('contact_id', '=', seat.contact_id.id),
                    ('active', '=', True),
                    ('id', '!=', seat.id)
                ])
                
                if duplicate_seats:
                    raise ValidationError(_(
                        f"Contact '{seat.contact_id.name}' is already assigned an active seat "
                        f"in subscription '{seat.subscription_id.name}'"
                    ))
    
    @api.constrains('subscription_id')
    def _check_subscription_type(self):
        """Ensure subscription supports seat management"""
        for seat in self:
            if (seat.subscription_id and 
                seat.subscription_id.subscription_type != 'enterprise'):
                raise ValidationError(_(
                    "Seats can only be assigned to enterprise subscriptions"
                ))

    # ========================================================================
    # LIFECYCLE METHODS
    # ========================================================================
    
    @api.model_create_multi
    def create(self, vals_list):
        """Enhanced create with automatic portal access setup"""
        seats = super().create(vals_list)
        
        for seat in seats:
            try:
                # Set up portal access for new seat
                seat._setup_portal_access()
                
                # Grant member benefits
                seat._grant_member_benefits()
                
                # Log seat assignment
                seat.subscription_id.message_post(
                    body=f"Seat assigned to {seat.contact_id.name} on {seat.assigned_date}",
                    message_type='notification'
                )
                
                _logger.info(f"Created seat {seat.id} for {seat.contact_id.name} in subscription {seat.subscription_id.id}")
                
            except Exception as e:
                _logger.error(f"Error setting up seat {seat.id}: {str(e)}")
                # Don't fail the creation, but log the issue
        
        return seats
    
    def write(self, vals):
        """Enhanced write with status change handling"""
        # Track deactivation
        if 'active' in vals:
            for seat in self:
                if not vals['active'] and seat.active:
                    # Being deactivated
                    if 'deactivated_date' not in vals:
                        vals['deactivated_date'] = fields.Date.today()
                    if 'deactivated_by_user_id' not in vals:
                        vals['deactivated_by_user_id'] = self.env.user.id
                elif vals['active'] and not seat.active:
                    # Being reactivated
                    vals.update({
                        'deactivated_date': False,
                        'deactivated_by_user_id': False,
                        'deactivation_reason': False,
                        'deactivation_notes': False,
                    })
        
        result = super().write(vals)
        
        # Handle status changes
        if 'active' in vals:
            for seat in self:
                if vals['active']:
                    seat._setup_portal_access()
                    seat._grant_member_benefits()
                else:
                    seat._revoke_portal_access()
                    seat._revoke_member_benefits()
        
        # Handle contact changes
        if 'contact_id' in vals:
            for seat in self:
                if seat.active:
                    seat._setup_portal_access()
                    seat._grant_member_benefits()
        
        return result
    
    def unlink(self):
        """Enhanced unlink with cleanup"""
        for seat in self:
            # Revoke access before deletion
            if seat.active:
                seat._revoke_portal_access()
                seat._revoke_member_benefits()
            
            # Log seat removal
            seat.subscription_id.message_post(
                body=f"Seat for {seat.contact_id.name} removed from subscription",
                message_type='notification'
            )
        
        return super().unlink()

    # ========================================================================
    # PORTAL ACCESS MANAGEMENT (Layer 2 integration)
    # ========================================================================
    
    def _setup_portal_access(self):
        """Set up portal access for seat holder"""
        self.ensure_one()
        
        if not self.active or not self.contact_id:
            return
        
        try:
            # Get portal access configuration from subscription tier
            if self.subscription_id.tier_id:
                tier_config = self.subscription_id.tier_id.get_benefit_configuration()
                
                if tier_config.get('grants_portal_access'):
                    # Ensure contact has portal user
                    if not self.contact_id.user_ids:
                        # Create portal user
                        user_vals = {
                            'name': self.contact_id.name,
                            'login': self.contact_id.email,
                            'email': self.contact_id.email,
                            'partner_id': self.contact_id.id,
                            'groups_id': [(6, 0, [self.env.ref('base.group_portal').id])],
                            'active': True,
                        }
                        
                        portal_user = self.env['res.users'].sudo().create(user_vals)
                        self.portal_user_id = portal_user.id
                    else:
                        # Use existing user
                        self.portal_user_id = self.contact_id.user_ids[0].id
                    
                    # Add portal groups from tier
                    portal_group_ids = tier_config.get('portal_groups', [])
                    if portal_group_ids and self.portal_user_id:
                        self.portal_user_id.sudo().write({
                            'groups_id': [(4, group_id) for group_id in portal_group_ids]
                        })
                        self.portal_group_ids = [(6, 0, portal_group_ids)]
        
        except Exception as e:
            _logger.error(f"Failed to setup portal access for seat {self.id}: {str(e)}")
    
    def _revoke_portal_access(self):
        """Revoke portal access for seat holder"""
        self.ensure_one()
        
        if self.portal_user_id:
            try:
                # Remove portal groups granted by this seat
                if self.portal_group_ids:
                    self.portal_user_id.sudo().write({
                        'groups_id': [(3, group_id) for group_id in self.portal_group_ids.ids]
                    })
                
                # Check if user has other active seats
                other_active_seats = self.search([
                    ('contact_id', '=', self.contact_id.id),
                    ('active', '=', True),
                    ('id', '!=', self.id)
                ])
                
                if not other_active_seats:
                    # No other active seats, can deactivate portal access
                    self.portal_user_id.sudo().active = False
                
                self.portal_group_ids = [(5, 0, 0)]  # Clear portal groups
                
            except Exception as e:
                _logger.error(f"Failed to revoke portal access for seat {self.id}: {str(e)}")
    
    def _grant_member_benefits(self):
        """Grant member benefits to seat holder using ams_products_base integration"""
        self.ensure_one()
        
        if not self.active:
            return
        
        try:
            # Get benefits from tier configuration
            if self.subscription_id.tier_id:
                tier_config = self.subscription_id.tier_id.get_benefit_configuration()
                benefit_products = tier_config.get('benefit_products', [])
                
                if benefit_products:
                    self.member_benefits_granted = [(6, 0, benefit_products)]
                
                # Update contact as active member
                self.contact_id.sudo().write({
                    'is_member': True,
                    'membership_status': 'active',
                })
        
        except Exception as e:
            _logger.error(f"Failed to grant benefits for seat {self.id}: {str(e)}")
    
    def _revoke_member_benefits(self):
        """Revoke member benefits from seat holder"""
        self.ensure_one()
        
        try:
            # Clear benefits
            self.member_benefits_granted = [(5, 0, 0)]
            
            # Check if contact has other active seats or subscriptions
            other_memberships = self.env['ams.subscription'].search([
                '|',
                ('partner_id', '=', self.contact_id.id),
                ('seat_ids.contact_id', '=', self.contact_id.id),
                ('seat_ids.active', '=', True),
                ('state', '=', 'active'),
                ('id', '!=', self.subscription_id.id)
            ])
            
            if not other_memberships:
                # No other active memberships, revoke member status
                self.contact_id.sudo().write({
                    'is_member': False,
                    'membership_status': 'former',
                })
        
        except Exception as e:
            _logger.error(f"Failed to revoke benefits for seat {self.id}: {str(e)}")

    # ========================================================================
    # BUSINESS METHODS
    # ========================================================================
    
    def action_activate_seat(self):
        """Activate this seat"""
        self.ensure_one()
        
        if self.active:
            raise UserError(_("This seat is already active"))
        
        # Check seat availability
        subscription = self.subscription_id
        if subscription.used_seats >= subscription.total_seats:
            raise UserError(_(
                f"Cannot activate seat. Subscription has {subscription.total_seats} seats "
                f"and {subscription.used_seats} are already in use."
            ))
        
        self.write({
            'active': True,
            'deactivated_date': False,
            'deactivated_by_user_id': False,
            'deactivation_reason': False,
            'deactivation_notes': False,
        })
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': f'Seat activated for {self.contact_id.name}',
                'type': 'success',
            }
        }
    
    def action_deactivate_seat(self):
        """Deactivate this seat with reason"""
        self.ensure_one()
        
        if not self.active:
            raise UserError(_("This seat is already inactive"))
        
        return {
            'type': 'ir.actions.act_window',
            'name': 'Deactivate Seat',
            'res_model': 'ams.seat.deactivation.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_seat_id': self.id,
            }
        }
    
    def action_transfer_seat(self):
        """Transfer seat to another contact"""
        self.ensure_one()
        
        return {
            'type': 'ir.actions.act_window',
            'name': 'Transfer Seat',
            'res_model': 'ams.seat.transfer.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_seat_id': self.id,
                'default_old_contact_id': self.contact_id.id,
                'default_subscription_id': self.subscription_id.id,
            }
        }
    
    def action_view_contact(self):
        """View the assigned contact"""
        self.ensure_one()
        
        return {
            'type': 'ir.actions.act_window',
            'name': f'Contact: {self.contact_id.name}',
            'res_model': 'res.partner',
            'res_id': self.contact_id.id,
            'view_mode': 'form',
            'target': 'current',
        }
    
    def action_access_portal(self):
        """Open portal for this seat holder"""
        self.ensure_one()
        
        if not self.has_portal_access:
            raise UserError(_("This seat holder does not have portal access"))
        
        return {
            'type': 'ir.actions.act_url',
            'url': '/my',
            'target': 'new',
        }

    # ========================================================================
    # REPORTING AND ANALYTICS
    # ========================================================================
    
    def get_seat_utilization_report(self):
        """Get seat utilization analytics"""
        self.ensure_one()
        
        return {
            'seat_info': {
                'contact_name': self.contact_id.name,
                'subscription_name': self.subscription_id.name,
                'assigned_date': self.assigned_date,
                'duration_days': self.seat_duration_days,
                'is_active': self.active,
                'role': self.seat_role,
            },
            'access_stats': {
                'last_access': self.last_access_date,
                'access_count': self.access_count,
                'has_portal_access': self.has_portal_access,
            },
            'benefits': {
                'benefits_granted': self.member_benefits_granted.mapped('name'),
                'portal_groups': self.portal_group_ids.mapped('name'),
            }
        }
    
    @api.model
    def get_seat_utilization_summary(self, subscription_ids=None):
        """Get summary of seat utilization across subscriptions"""
        domain = [('subscription_id.subscription_type', '=', 'enterprise')]
        if subscription_ids:
            domain.append(('subscription_id', 'in', subscription_ids))
        
        seats = self.search(domain)
        
        return {
            'total_seats': len(seats),
            'active_seats': len(seats.filtered('active')),
            'inactive_seats': len(seats.filtered(lambda s: not s.active)),
            'portal_users': len(seats.filtered('has_portal_access')),
            'avg_duration': sum(seats.mapped('seat_duration_days')) / len(seats) if seats else 0,
            'by_role': {
                role[0]: len(seats.filtered(lambda s: s.seat_role == role[0]))
                for role in self._fields['seat_role'].selection
            }
        }

    # ========================================================================
    # NAME AND DISPLAY
    # ========================================================================
    
    def name_get(self):
        """Enhanced name display"""
        result = []
        for seat in self:
            name = f"{seat.contact_id.name} ({seat.subscription_name})"
            
            if not seat.active:
                name = f"{name} [Inactive]"
            
            if seat.seat_role != 'standard':
                name = f"{name} - {dict(seat._fields['seat_role'].selection)[seat.seat_role]}"
            
            result.append((seat.id, name))
        
        return result

    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        """Enhanced name search"""
        args = args or []
        
        if name:
            domain = [
                '|', '|', '|',
                ('contact_id.name', operator, name),
                ('contact_id.email', operator, name),
                ('subscription_id.name', operator, name),
                ('department', operator, name)
            ]
            args = domain + args
        
        return self._search(args, limit=limit, access_rights_uid=name_get_uid)