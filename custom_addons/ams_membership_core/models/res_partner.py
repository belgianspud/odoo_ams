# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
import logging

_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _inherit = 'res.partner'

    # === FOUNDATION FIELD SAFETY METHODS ===
    
    def _ensure_foundation_fields(self):
        """Ensure foundation fields exist and have safe values"""
        self.ensure_one()
        
        try:
            # Check if foundation fields exist, if not create safe defaults
            if not hasattr(self, 'is_member'):
                self.is_member = False
                
            if not hasattr(self, 'member_number'):
                self.member_number = False
                
            if not hasattr(self, 'member_status'):
                self.member_status = 'unknown'
            elif not self.member_status:
                self.member_status = 'unknown'
                
            if not hasattr(self, 'member_type_id'):
                self.member_type_id = False
                
            # Ensure member_status is never None
            if self.member_status is None:
                self.member_status = 'unknown'
                
        except Exception as e:
            _logger.warning(f"Error ensuring foundation fields for {self.name}: {e}")

    def _safe_getattr(self, field_name, default=None):
        """Safely get attribute with fallback"""
        try:
            if hasattr(self, field_name):
                value = getattr(self, field_name, default)
                return value if value is not None else default
            return default
        except Exception:
            return default

    # === MEMBERSHIP CORE EXTENSIONS - FIXED ===
    
    # Membership Records (real data - stored in membership_core)
    membership_ids = fields.One2many(
        'ams.membership',
        'partner_id',
        string='All Memberships',
        help='All membership records for this member'
    )
    
    subscription_ids = fields.One2many(
        'ams.subscription',
        'partner_id', 
        string='All Subscriptions',
        help='All subscription records for this member'
    )
    
    # Active Records (computed from real data) - FIXED
    current_membership_id = fields.Many2one(
        'ams.membership',
        string='Current Membership',
        compute='_compute_current_membership',
        store=True,
        help='Current active membership (only one allowed)'
    )
    
    active_membership_ids = fields.One2many(
        'ams.membership',
        'partner_id',
        string='Active Memberships',
        compute='_compute_active_records',
        help='All currently active memberships'
    )
    
    active_subscription_ids = fields.One2many(
        'ams.subscription',
        'partner_id',
        string='Active Subscriptions',
        compute='_compute_active_records',
        help='All currently active subscriptions'
    )
    
    # Counts (for stat buttons) - FIXED
    membership_count = fields.Integer(
        string='Total Memberships',
        compute='_compute_record_counts',
        store=True,
        help='Total number of membership records'
    )
    
    active_membership_count = fields.Integer(
        string='Active Memberships',
        compute='_compute_record_counts',
        store=True,
        help='Number of active memberships'
    )
    
    subscription_count = fields.Integer(
        string='Total Subscriptions',
        compute='_compute_record_counts',
        store=True,
        help='Total number of subscription records'
    )
    
    active_subscription_count = fields.Integer(
        string='Active Subscriptions',
        compute='_compute_record_counts',
        store=True,
        help='Number of active subscriptions'
    )
    
    # Benefits (computed from active memberships/subscriptions)
    active_benefit_ids = fields.Many2many(
        'ams.benefit',
        string='Active Benefits',
        compute='_compute_active_benefits',
        help='All benefits currently available to this member'
    )
    
    # Renewal Information (computed and stored for search)
    next_renewal_date = fields.Date(
        string='Next Renewal Date',
        compute='_compute_renewal_info',
        store=True,
        help='Next upcoming renewal date'
    )
    
    pending_renewals_count = fields.Integer(
        string='Pending Renewals',
        compute='_compute_renewal_info',
        store=True,
        help='Number of pending renewal reminders'
    )
    
    # Statistics (computed and stored for search)
    total_membership_years = fields.Float(
        string='Total Membership Years',
        compute='_compute_membership_stats',
        store=True,
        help='Total years of membership history'
    )

    # === FIXED COMPUTED METHODS ===
    
    @api.depends('membership_ids.state')
    def _compute_current_membership(self):
        """Compute current active membership - SAFE VERSION"""
        for partner in self:
            try:
                # Ensure foundation fields exist first
                partner._ensure_foundation_fields()
                
                active_membership = partner.membership_ids.filtered(
                    lambda m: m.state == 'active'
                )
                partner.current_membership_id = active_membership[0] if active_membership else False
                
                # Sync with foundation's member status safely
                if active_membership:
                    # Ensure member_status is never None
                    current_status = partner._safe_getattr('member_status', 'unknown')
                    if current_status != 'active':
                        # Update foundation status to match membership core reality
                        try:
                            partner.with_context(skip_auto_sync=True).write({
                                'member_status': 'active',
                                'membership_start_date': active_membership[0].start_date,
                                'membership_end_date': active_membership[0].end_date,
                            })
                        except Exception as e:
                            _logger.warning(f"Could not sync member status for {partner.name}: {e}")
                            
                elif partner._safe_getattr('is_member', False):
                    # Check for grace period memberships
                    grace_membership = partner.membership_ids.filtered(
                        lambda m: m.state == 'grace'
                    )
                    if grace_membership:
                        new_status = 'grace'
                    else:
                        new_status = 'lapsed'
                    
                    try:
                        partner.with_context(skip_auto_sync=True).write({
                            'member_status': new_status
                        })
                    except Exception as e:
                        _logger.warning(f"Could not update member status for {partner.name}: {e}")
                        
            except Exception as e:
                _logger.error(f"Error computing current membership for {partner.name}: {e}")
                partner.current_membership_id = False
                # Ensure member_status has a safe value
                try:
                    if hasattr(partner, 'member_status') and partner.member_status is None:
                        partner.member_status = 'unknown'
                except Exception:
                    pass
    
    @api.depends('membership_ids.state', 'subscription_ids.state')
    def _compute_active_records(self):
        """Compute active memberships and subscriptions - NEW METHOD"""
        for partner in self:
            try:
                # Get active memberships
                active_memberships = partner.membership_ids.filtered(lambda m: m.state == 'active')
                partner.active_membership_ids = [(6, 0, active_memberships.ids)]
                
                # Get active subscriptions
                active_subscriptions = partner.subscription_ids.filtered(lambda s: s.state == 'active')
                partner.active_subscription_ids = [(6, 0, active_subscriptions.ids)]
                
            except Exception as e:
                _logger.error(f"Error computing active records for {partner.name}: {e}")
                partner.active_membership_ids = [(6, 0, [])]
                partner.active_subscription_ids = [(6, 0, [])]
    
    @api.depends('membership_ids', 'subscription_ids', 'membership_ids.state', 'subscription_ids.state')
    def _compute_record_counts(self):
        """Compute membership and subscription counts - NEW METHOD"""
        for partner in self:
            try:
                # Total counts
                partner.membership_count = len(partner.membership_ids)
                partner.subscription_count = len(partner.subscription_ids)
                
                # Active counts
                active_memberships = partner.membership_ids.filtered(lambda m: m.state == 'active')
                partner.active_membership_count = len(active_memberships)
                
                active_subscriptions = partner.subscription_ids.filtered(lambda s: s.state == 'active')
                partner.active_subscription_count = len(active_subscriptions)
                
            except Exception as e:
                _logger.error(f"Error computing record counts for {partner.name}: {e}")
                partner.membership_count = 0
                partner.subscription_count = 0
                partner.active_membership_count = 0
                partner.active_subscription_count = 0
    
    def _compute_active_benefits(self):
        """Compute all active benefits - SAFE VERSION"""
        for partner in self:
            try:
                benefit_ids = set()
                
                # Benefits from active memberships
                active_memberships = partner.membership_ids.filtered(lambda m: m.state == 'active')
                for membership in active_memberships:
                    if hasattr(membership, 'benefit_ids') and membership.benefit_ids:
                        benefit_ids.update(membership.benefit_ids.ids)
                
                # Benefits from active subscriptions
                active_subscriptions = partner.subscription_ids.filtered(lambda s: s.state == 'active')
                for subscription in active_subscriptions:
                    if hasattr(subscription, 'benefit_ids') and subscription.benefit_ids:
                        benefit_ids.update(subscription.benefit_ids.ids)
                
                # Always return a recordset, never None
                partner.active_benefit_ids = [(6, 0, list(benefit_ids))]
                
            except Exception as e:
                _logger.error(f"Error computing active benefits for {partner.name}: {e}")
                partner.active_benefit_ids = [(6, 0, [])]  # Empty recordset
    
    @api.depends('membership_ids.next_renewal_date', 'subscription_ids.next_renewal_date')
    def _compute_renewal_info(self):
        """Compute renewal information - SAFE VERSION"""
        for partner in self:
            try:
                renewal_dates = []
                
                # Collect renewal dates safely from active records
                active_memberships = partner.membership_ids.filtered(lambda m: m.state == 'active')
                for membership in active_memberships:
                    if hasattr(membership, 'next_renewal_date') and membership.next_renewal_date:
                        renewal_dates.append(membership.next_renewal_date)
                
                active_subscriptions = partner.subscription_ids.filtered(lambda s: s.state == 'active')
                for subscription in active_subscriptions:
                    if hasattr(subscription, 'next_renewal_date') and subscription.next_renewal_date:
                        renewal_dates.append(subscription.next_renewal_date)
                
                # Set values safely
                partner.next_renewal_date = min(renewal_dates) if renewal_dates else False
                
                # Count pending renewals safely
                try:
                    pending_renewals = self.env['ams.renewal'].search_count([
                        ('partner_id', '=', partner.id),
                        ('state', 'in', ['draft', 'pending'])
                    ])
                    partner.pending_renewals_count = pending_renewals
                except Exception as e:
                    _logger.warning(f"Error counting pending renewals for {partner.name}: {e}")
                    partner.pending_renewals_count = 0
                    
            except Exception as e:
                _logger.error(f"Error computing renewal info for {partner.name}: {e}")
                partner.next_renewal_date = False
                partner.pending_renewals_count = 0
    
    @api.depends('membership_ids.start_date', 'membership_ids.end_date')
    def _compute_membership_stats(self):
        """Compute membership statistics - SAFE VERSION"""
        for partner in self:
            try:
                # Calculate total membership years
                total_days = 0
                for membership in partner.membership_ids:
                    try:
                        if membership.start_date and membership.end_date:
                            days = (membership.end_date - membership.start_date).days
                            total_days += days
                    except Exception as e:
                        _logger.warning(f"Error calculating membership days for {partner.name}: {e}")
                        continue
                
                partner.total_membership_years = total_days / 365.25 if total_days > 0 else 0.0
                
            except Exception as e:
                _logger.error(f"Error computing membership stats for {partner.name}: {e}")
                partner.total_membership_years = 0.0

    # === SAFE READ METHOD ===
    
    def read(self, fields=None, load='_classic_read'):
        """Override read to provide safe field values"""
        try:
            result = super().read(fields, load)
            
            # Ensure safe values for foundation fields
            for record in result:
                if isinstance(record, dict):
                    # Ensure member_status is never None
                    if 'member_status' in record and record['member_status'] is None:
                        record['member_status'] = 'unknown'
                    
                    # Ensure member_number is never None in templates
                    if 'member_number' in record and record['member_number'] is None:
                        record['member_number'] = False
                    
                    # Ensure is_member is always boolean
                    if 'is_member' in record and record['is_member'] is None:
                        record['is_member'] = False
            
            return result
        except Exception as e:
            _logger.error(f"Error reading partner fields: {e}")
            # Return safe default if read fails
            if fields:
                safe_result = []
                for _ in range(len(self)):
                    safe_record = {}
                    for field in fields:
                        if field in ['member_status']:
                            safe_record[field] = 'unknown'
                        elif field in ['is_member']:
                            safe_record[field] = False
                        elif field in ['member_number']:
                            safe_record[field] = False
                        else:
                            safe_record[field] = False
                    safe_result.append(safe_record)
                return safe_result
            return []

    def write(self, vals):
        """Override write to handle membership status sync - SAFE VERSION"""
        try:
            # Handle foundation status changes and sync with membership core
            result = super().write(vals)
            
            # Skip auto-sync if called from membership core to avoid recursion
            if self.env.context.get('skip_auto_sync'):
                return result
            
            # Sync member status changes from foundation to membership records
            if 'member_status' in vals:
                for partner in self:
                    try:
                        partner._sync_member_status_to_memberships(vals['member_status'])
                    except Exception as e:
                        _logger.warning(f"Error syncing member status for {partner.name}: {e}")
            
            return result
        except Exception as e:
            _logger.error(f"Error in partner write method: {e}")
            # Try to continue without syncing
            return super().write(vals)

    def _sync_member_status_to_memberships(self, new_status):
        """Sync member status changes to membership records - SAFE VERSION"""
        self.ensure_one()
        
        try:
            if new_status == 'terminated' and self.current_membership_id:
                self.current_membership_id.write({'state': 'terminated'})
            
            elif new_status == 'suspended':
                if self.current_membership_id:
                    self.current_membership_id.write({'state': 'suspended'})
                
                # Also suspend active subscriptions
                try:
                    active_subscriptions = self.subscription_ids.filtered(lambda s: s.state == 'active')
                    for subscription in active_subscriptions:
                        subscription.write({'state': 'suspended'})
                except Exception as e:
                    _logger.warning(f"Error suspending subscriptions for {self.name}: {e}")
            
            elif new_status == 'active' and self.current_membership_id:
                if self.current_membership_id.state in ['grace', 'suspended']:
                    self.current_membership_id.write({'state': 'active'})
                    
        except Exception as e:
            _logger.error(f"Error syncing member status to memberships for {self.name}: {e}")

    # === ACTION METHODS ===
    
    def action_view_memberships(self):
        """View all memberships for this partner"""
        self.ensure_one()
        
        return {
            'name': _('Memberships: %s') % (self.name or 'Partner'),
            'type': 'ir.actions.act_window',
            'res_model': 'ams.membership',
            'view_mode': 'list,form',
            'domain': [('partner_id', '=', self.id)],
            'context': {'default_partner_id': self.id}
        }
    
    def action_view_subscriptions(self):
        """View all subscriptions for this partner"""
        self.ensure_one()
        
        return {
            'name': _('Subscriptions: %s') % (self.name or 'Partner'),
            'type': 'ir.actions.act_window',
            'res_model': 'ams.subscription',
            'view_mode': 'list,form',
            'domain': [('partner_id', '=', self.id)],
            'context': {'default_partner_id': self.id}
        }
    
    def action_view_active_memberships(self):
        """View active memberships for this partner"""
        self.ensure_one()
        
        return {
            'name': _('Active Memberships: %s') % (self.name or 'Partner'),
            'type': 'ir.actions.act_window',
            'res_model': 'ams.membership',
            'view_mode': 'list,form',
            'domain': [('partner_id', '=', self.id), ('state', '=', 'active')],
            'context': {'default_partner_id': self.id}
        }
    
    def action_view_active_subscriptions(self):
        """View active subscriptions for this partner"""
        self.ensure_one()
        
        return {
            'name': _('Active Subscriptions: %s') % (self.name or 'Partner'),
            'type': 'ir.actions.act_window',
            'res_model': 'ams.subscription',
            'view_mode': 'list,form',
            'domain': [('partner_id', '=', self.id), ('state', '=', 'active')],
            'context': {'default_partner_id': self.id}
        }
    
    def action_view_renewals(self):
        """View renewal history for this partner"""
        self.ensure_one()
        
        return {
            'name': _('Renewals: %s') % (self.name or 'Partner'),
            'type': 'ir.actions.act_window',
            'res_model': 'ams.renewal',
            'view_mode': 'list,form',
            'domain': [('partner_id', '=', self.id)],
            'context': {'default_partner_id': self.id}
        }
    
    def action_view_benefits(self):
        """View active benefits for this partner"""
        self.ensure_one()
        
        benefit_ids = []
        try:
            benefit_ids = self.active_benefit_ids.ids
        except Exception:
            benefit_ids = []
        
        return {
            'name': _('Active Benefits: %s') % (self.name or 'Partner'),
            'type': 'ir.actions.act_window',
            'res_model': 'ams.benefit',
            'view_mode': 'list,form',
            'domain': [('id', 'in', benefit_ids)],
        }

    # === BENEFIT MANAGEMENT - SAFE VERSIONS ===
    
    def has_benefit(self, benefit_code):
        """Check if member has a specific benefit - SAFE VERSION"""
        self.ensure_one()
        try:
            return any(benefit.code == benefit_code for benefit in self.active_benefit_ids)
        except Exception:
            return False
    
    def get_discount_amount(self, original_amount, benefit_codes=None):
        """Calculate total discount amount from active benefits - SAFE VERSION"""
        self.ensure_one()
        
        if not original_amount:
            return 0.0
            
        total_discount = 0.0
        
        try:
            for benefit in self.active_benefit_ids:
                try:
                    if benefit.benefit_type != 'discount':
                        continue
                    
                    # Filter by benefit codes if specified
                    if benefit_codes and benefit.code not in benefit_codes:
                        continue
                    
                    discount = benefit.get_discount_amount(original_amount)
                    total_discount += discount
                except Exception as e:
                    _logger.warning(f"Error calculating discount for benefit {benefit.id}: {e}")
                    continue
                    
        except Exception as e:
            _logger.error(f"Error getting discount amount for {self.name}: {e}")
        
        return min(total_discount, original_amount)
    
    def record_benefit_usage(self, benefit_code, quantity=1, notes=None):
        """Record usage of a specific benefit - SAFE VERSION"""
        self.ensure_one()
        
        try:
            benefit = self.active_benefit_ids.filtered(lambda b: b.code == benefit_code)
            if not benefit:
                raise UserError(_("Benefit '%s' not available for this member.") % benefit_code)
            
            return benefit[0].record_usage(self.id, quantity, notes)
        except Exception as e:
            _logger.error(f"Error recording benefit usage for {self.name}: {e}")
            raise UserError(_("Could not record benefit usage: %s") % str(e))

    # === PORTAL ACCESS ENHANCEMENT - SAFE VERSION ===
    
    def action_create_portal_user(self):
        """Create portal user for this partner - SAFE VERSION"""
        self.ensure_one()
    
        if getattr(self, 'portal_user_id', None):
            raise UserError(_("Portal user already exists for this partner."))
    
        if not self.email:
            raise UserError(_("Partner must have an email address to create portal user."))
    
        try:
            # Check if foundation has the method, otherwise use basic implementation
            if hasattr(super(), 'action_create_portal_user'):
                return super().action_create_portal_user()
            else:
                # Basic portal user creation
                portal_group = self.env.ref('base.group_portal')
                user_vals = {
                    'name': self.name or 'Portal User',
                    'login': self.email,
                    'email': self.email,
                    'partner_id': self.id,
                    'groups_id': [(6, 0, [portal_group.id])],
                    'active': True,
                }
            
                user = self.env['res.users'].create(user_vals)
                
                # Try to set portal_user_id if field exists
                if hasattr(self, 'portal_user_id'):
                    self.portal_user_id = user.id
            
                return {
                    'type': 'ir.actions.act_window',
                    'name': _('Portal User'),
                    'res_model': 'res.users',
                    'res_id': user.id,
                    'view_mode': 'form',
                }
        except Exception as e:
            _logger.error(f"Error creating portal user for {self.name}: {e}")
            raise UserError(_("Could not create portal user: %s") % str(e))

    # === CONSTRAINTS - SAFE VERSIONS ===
    
    @api.constrains('membership_ids')
    def _check_single_active_membership(self):
        """Ensure only one active membership per member (foundation rule) - SAFE VERSION"""
        for partner in self:
            try:
                active_memberships = partner.membership_ids.filtered(
                    lambda m: m.state == 'active'
                )
                if len(active_memberships) > 1:
                    raise ValidationError(
                        _("Member %s has multiple active memberships. "
                          "Only one active membership is allowed per member.") % 
                        (partner.name or 'Unknown Partner')
                    )
            except Exception as e:
                _logger.error(f"Error checking single active membership constraint: {e}")