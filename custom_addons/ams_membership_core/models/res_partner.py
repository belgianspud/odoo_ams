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

    # === MEMBERSHIP CORE EXTENSIONS - ENHANCED FOR CHAPTERS ===
    
    # Membership Records (real data - stored in membership_core)
    membership_ids = fields.One2many(
        'ams.membership',
        'partner_id',
        string='All Memberships',
        help='All membership records for this member (regular and chapter)'
    )
    
    subscription_ids = fields.One2many(
        'ams.subscription',
        'partner_id', 
        string='All Subscriptions',
        help='All subscription records for this member'
    )
    
    # Active Records (computed from real data) - ENHANCED FOR CHAPTERS
    current_membership_id = fields.Many2one(
        'ams.membership',
        string='Current Regular Membership',
        compute='_compute_current_membership',
        store=True,
        help='Current active regular membership (only one allowed)'
    )
    
    active_membership_ids = fields.One2many(
        'ams.membership',
        'partner_id',
        string='Active Memberships',
        compute='_compute_active_records',
        help='All currently active memberships (regular and chapter)'
    )
    
    active_subscription_ids = fields.One2many(
        'ams.subscription',
        'partner_id',
        string='Active Subscriptions',
        compute='_compute_active_records',
        help='All currently active subscriptions'
    )
    
    # ENHANCED: Chapter-specific computed fields
    active_chapter_memberships = fields.One2many(
        'ams.membership',
        'partner_id',
        string='Active Chapter Memberships',
        compute='_compute_chapter_records',
        help='Currently active chapter memberships'
    )
    
    chapter_membership_ids = fields.One2many(
        'ams.membership',
        'partner_id',
        string='All Chapter Memberships',
        compute='_compute_chapter_records',
        help='All chapter membership records'
    )
    
    # Counts (for stat buttons) - ENHANCED FOR CHAPTERS
    membership_count = fields.Integer(
        string='Total Memberships',
        compute='_compute_record_counts',
        store=True,
        help='Total number of membership records (regular and chapter)'
    )
    
    active_membership_count = fields.Integer(
        string='Active Memberships',
        compute='_compute_record_counts',
        store=True,
        help='Number of active memberships (regular and chapter)'
    )
    
    regular_membership_count = fields.Integer(
        string='Regular Memberships',
        compute='_compute_record_counts',
        store=True,
        help='Number of regular (non-chapter) memberships'
    )
    
    chapter_membership_count = fields.Integer(
        string='Chapter Memberships',
        compute='_compute_record_counts',
        store=True,
        help='Number of chapter memberships'
    )
    
    active_chapter_count = fields.Integer(
        string='Active Chapters',
        compute='_compute_record_counts',
        store=True,
        help='Number of active chapter memberships'
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
    
    # ENHANCED: Chapter engagement and analytics
    chapter_engagement_score = fields.Float(
        string='Chapter Engagement Score',
        compute='_compute_chapter_analytics',
        store=True,
        help='Average engagement score across all chapter memberships'
    )
    
    chapter_leadership_roles = fields.Integer(
        string='Chapter Leadership Roles',
        compute='_compute_chapter_analytics',
        store=True,
        help='Number of chapter leadership positions held'
    )
    
    total_chapter_years = fields.Float(
        string='Total Chapter Years',
        compute='_compute_chapter_analytics',
        store=True,
        help='Total years of chapter membership across all chapters'
    )
    
    # Benefits (computed from active memberships/subscriptions)
    active_benefit_ids = fields.Many2many(
        'ams.benefit',
        string='Active Benefits',
        compute='_compute_active_benefits',
        help='All benefits currently available to this member'
    )
    
    # Chapter-specific benefits
    chapter_benefit_ids = fields.Many2many(
        'ams.benefit',
        string='Chapter Benefits',
        compute='_compute_active_benefits',
        help='Benefits from chapter memberships only'
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
    
    chapter_renewals_count = fields.Integer(
        string='Chapter Renewals Due',
        compute='_compute_renewal_info',
        store=True,
        help='Number of chapter renewals due soon'
    )
    
    # Statistics (computed and stored for search)
    total_membership_years = fields.Float(
        string='Total Membership Years',
        compute='_compute_membership_stats',
        store=True,
        help='Total years of membership history (regular memberships only)'
    )

    # === ENHANCED COMPUTED METHODS FOR CHAPTERS ===
    
    @api.depends('membership_ids.state', 'membership_ids.is_chapter_membership')
    def _compute_current_membership(self):
        """Compute current active REGULAR membership - ENHANCED for chapter awareness"""
        for partner in self:
            try:
                # Ensure foundation fields exist first
                partner._ensure_foundation_fields()
                
                # Get active REGULAR membership only (not chapter)
                active_regular_membership = partner.membership_ids.filtered(
                    lambda m: m.state == 'active' and not m.is_chapter_membership
                )
                partner.current_membership_id = active_regular_membership[0] if active_regular_membership else False
                
                # Sync with foundation's member status safely for regular memberships
                if active_regular_membership:
                    # Ensure member_status is never None
                    current_status = partner._safe_getattr('member_status', 'unknown')
                    if current_status != 'active':
                        # Update foundation status to match membership core reality
                        try:
                            partner.with_context(skip_auto_sync=True).write({
                                'member_status': 'active',
                                'membership_start_date': active_regular_membership[0].start_date,
                                'membership_end_date': active_regular_membership[0].end_date,
                            })
                        except Exception as e:
                            _logger.warning(f"Could not sync member status for {partner.name}: {e}")
                            
                elif partner._safe_getattr('is_member', False):
                    # Check for grace period regular memberships
                    grace_membership = partner.membership_ids.filtered(
                        lambda m: m.state == 'grace' and not m.is_chapter_membership
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
        """Compute active memberships and subscriptions - ENHANCED for chapters"""
        for partner in self:
            try:
                # Get active memberships (both regular and chapter)
                active_memberships = partner.membership_ids.filtered(lambda m: m.state == 'active')
                partner.active_membership_ids = [(6, 0, active_memberships.ids)]
                
                # Get active subscriptions
                active_subscriptions = partner.subscription_ids.filtered(lambda s: s.state == 'active')
                partner.active_subscription_ids = [(6, 0, active_subscriptions.ids)]
                
            except Exception as e:
                _logger.error(f"Error computing active records for {partner.name}: {e}")
                partner.active_membership_ids = [(6, 0, [])]
                partner.active_subscription_ids = [(6, 0, [])]
    
    @api.depends('membership_ids.state', 'membership_ids.is_chapter_membership')
    def _compute_chapter_records(self):
        """Compute chapter-specific membership records - NEW METHOD"""
        for partner in self:
            try:
                # Get all chapter memberships
                chapter_memberships = partner.membership_ids.filtered(lambda m: m.is_chapter_membership)
                partner.chapter_membership_ids = [(6, 0, chapter_memberships.ids)]
                
                # Get active chapter memberships
                active_chapters = chapter_memberships.filtered(lambda m: m.state == 'active')
                partner.active_chapter_memberships = [(6, 0, active_chapters.ids)]
                
            except Exception as e:
                _logger.error(f"Error computing chapter records for {partner.name}: {e}")
                partner.chapter_membership_ids = [(6, 0, [])]
                partner.active_chapter_memberships = [(6, 0, [])]
    
    @api.depends('membership_ids', 'subscription_ids', 'membership_ids.state', 'subscription_ids.state', 
                 'membership_ids.is_chapter_membership')
    def _compute_record_counts(self):
        """Compute membership and subscription counts - ENHANCED for chapters"""
        for partner in self:
            try:
                # Total counts
                all_memberships = partner.membership_ids
                partner.membership_count = len(all_memberships)
                partner.subscription_count = len(partner.subscription_ids)
                
                # Active counts
                active_memberships = all_memberships.filtered(lambda m: m.state == 'active')
                partner.active_membership_count = len(active_memberships)
                
                active_subscriptions = partner.subscription_ids.filtered(lambda s: s.state == 'active')
                partner.active_subscription_count = len(active_subscriptions)
                
                # ENHANCED: Chapter-specific counts
                chapter_memberships = all_memberships.filtered(lambda m: m.is_chapter_membership)
                regular_memberships = all_memberships.filtered(lambda m: not m.is_chapter_membership)
                
                partner.chapter_membership_count = len(chapter_memberships)
                partner.regular_membership_count = len(regular_memberships)
                
                active_chapters = chapter_memberships.filtered(lambda m: m.state == 'active')
                partner.active_chapter_count = len(active_chapters)
                
            except Exception as e:
                _logger.error(f"Error computing record counts for {partner.name}: {e}")
                partner.membership_count = 0
                partner.subscription_count = 0
                partner.active_membership_count = 0
                partner.active_subscription_count = 0
                partner.chapter_membership_count = 0
                partner.regular_membership_count = 0
                partner.active_chapter_count = 0
    
    @api.depends('membership_ids.chapter_engagement_score', 'membership_ids.chapter_role',
                 'membership_ids.start_date', 'membership_ids.is_chapter_membership')
    def _compute_chapter_analytics(self):
        """Compute chapter engagement and analytics - NEW METHOD"""
        for partner in self:
            try:
                chapter_memberships = partner.membership_ids.filtered(lambda m: m.is_chapter_membership)
                
                if chapter_memberships:
                    # Average engagement score
                    active_chapters = chapter_memberships.filtered(lambda m: m.state == 'active')
                    if active_chapters:
                        scores = [m.chapter_engagement_score for m in active_chapters if m.chapter_engagement_score > 0]
                        partner.chapter_engagement_score = sum(scores) / len(scores) if scores else 0.0
                    else:
                        partner.chapter_engagement_score = 0.0
                    
                    # Leadership roles count
                    leadership_roles = chapter_memberships.filtered(
                        lambda m: m.chapter_role in ['officer', 'board_member', 'president', 
                                                   'vice_president', 'secretary', 'treasurer']
                    )
                    partner.chapter_leadership_roles = len(leadership_roles)
                    
                    # Total chapter years
                    total_days = 0
                    for membership in chapter_memberships:
                        if membership.start_date and membership.end_date:
                            days = (membership.end_date - membership.start_date).days
                            total_days += days
                        elif membership.start_date:  # Active membership
                            days = (fields.Date.today() - membership.start_date).days
                            total_days += days
                    
                    partner.total_chapter_years = total_days / 365.25 if total_days > 0 else 0.0
                else:
                    partner.chapter_engagement_score = 0.0
                    partner.chapter_leadership_roles = 0
                    partner.total_chapter_years = 0.0
                    
            except Exception as e:
                _logger.error(f"Error computing chapter analytics for {partner.name}: {e}")
                partner.chapter_engagement_score = 0.0
                partner.chapter_leadership_roles = 0
                partner.total_chapter_years = 0.0
    
    def _compute_active_benefits(self):
        """Compute all active benefits - ENHANCED for chapter benefits"""
        for partner in self:
            try:
                all_benefit_ids = set()
                chapter_benefit_ids = set()
                
                # Benefits from active memberships (both regular and chapter)
                active_memberships = partner.membership_ids.filtered(lambda m: m.state == 'active')
                for membership in active_memberships:
                    if hasattr(membership, 'benefit_ids') and membership.benefit_ids:
                        all_benefit_ids.update(membership.benefit_ids.ids)
                        # Track chapter-specific benefits separately
                        if membership.is_chapter_membership:
                            chapter_benefit_ids.update(membership.benefit_ids.ids)
                
                # Benefits from active subscriptions
                active_subscriptions = partner.subscription_ids.filtered(lambda s: s.state == 'active')
                for subscription in active_subscriptions:
                    if hasattr(subscription, 'benefit_ids') and subscription.benefit_ids:
                        all_benefit_ids.update(subscription.benefit_ids.ids)
                
                # Always return recordsets, never None
                partner.active_benefit_ids = [(6, 0, list(all_benefit_ids))]
                partner.chapter_benefit_ids = [(6, 0, list(chapter_benefit_ids))]
                
            except Exception as e:
                _logger.error(f"Error computing active benefits for {partner.name}: {e}")
                partner.active_benefit_ids = [(6, 0, [])]
                partner.chapter_benefit_ids = [(6, 0, [])]
    
    @api.depends('membership_ids.next_renewal_date', 'subscription_ids.next_renewal_date',
                 'membership_ids.is_chapter_membership')
    def _compute_renewal_info(self):
        """Compute renewal information - ENHANCED for chapter renewals"""
        for partner in self:
            try:
                renewal_dates = []
                chapter_renewals = 0
                
                # Collect renewal dates safely from active records
                active_memberships = partner.membership_ids.filtered(lambda m: m.state == 'active')
                for membership in active_memberships:
                    if hasattr(membership, 'next_renewal_date') and membership.next_renewal_date:
                        renewal_dates.append(membership.next_renewal_date)
                        # Count chapter renewals due within 30 days
                        if (membership.is_chapter_membership and 
                            (membership.next_renewal_date - fields.Date.today()).days <= 30):
                            chapter_renewals += 1
                
                active_subscriptions = partner.subscription_ids.filtered(lambda s: s.state == 'active')
                for subscription in active_subscriptions:
                    if hasattr(subscription, 'next_renewal_date') and subscription.next_renewal_date:
                        renewal_dates.append(subscription.next_renewal_date)
                
                # Set values safely
                partner.next_renewal_date = min(renewal_dates) if renewal_dates else False
                partner.chapter_renewals_count = chapter_renewals
                
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
                partner.chapter_renewals_count = 0
    
    @api.depends('membership_ids.start_date', 'membership_ids.end_date', 'membership_ids.is_chapter_membership')
    def _compute_membership_stats(self):
        """Compute membership statistics - ENHANCED to exclude chapters from regular membership years"""
        for partner in self:
            try:
                # Calculate total REGULAR membership years (excluding chapters)
                regular_memberships = partner.membership_ids.filtered(lambda m: not m.is_chapter_membership)
                total_days = 0
                for membership in regular_memberships:
                    try:
                        if membership.start_date and membership.end_date:
                            days = (membership.end_date - membership.start_date).days
                            total_days += days
                        elif membership.start_date and membership.state == 'active':
                            # Active membership without end date - count to today
                            days = (fields.Date.today() - membership.start_date).days
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
        """Override write to handle membership status sync - ENHANCED for chapters"""
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
        """Sync member status changes to membership records - ENHANCED for chapters"""
        self.ensure_one()
        
        try:
            if new_status == 'terminated':
                # Terminate current regular membership
                if self.current_membership_id:
                    self.current_membership_id.write({'state': 'terminated'})
                
                # Also suspend active chapter memberships (chapters don't get terminated automatically)
                active_chapters = self.membership_ids.filtered(
                    lambda m: m.is_chapter_membership and m.state == 'active'
                )
                for chapter in active_chapters:
                    chapter.write({'state': 'suspended'})
            
            elif new_status == 'suspended':
                # Suspend current regular membership
                if self.current_membership_id:
                    self.current_membership_id.write({'state': 'suspended'})
                
                # Also suspend active chapter memberships
                active_chapters = self.membership_ids.filtered(
                    lambda m: m.is_chapter_membership and m.state == 'active'
                )
                for chapter in active_chapters:
                    chapter.write({'state': 'suspended'})
                
                # Also suspend active subscriptions
                try:
                    active_subscriptions = self.subscription_ids.filtered(lambda s: s.state == 'active')
                    for subscription in active_subscriptions:
                        subscription.write({'state': 'suspended'})
                except Exception as e:
                    _logger.warning(f"Error suspending subscriptions for {self.name}: {e}")
            
            elif new_status == 'active':
                # Reactivate current regular membership
                if self.current_membership_id and self.current_membership_id.state in ['grace', 'suspended']:
                    self.current_membership_id.write({'state': 'active'})
                
                # Reactivate suspended chapter memberships
                suspended_chapters = self.membership_ids.filtered(
                    lambda m: m.is_chapter_membership and m.state == 'suspended'
                )
                for chapter in suspended_chapters:
                    chapter.write({'state': 'active'})
                    
        except Exception as e:
            _logger.error(f"Error syncing member status to memberships for {self.name}: {e}")

    # === ENHANCED ACTION METHODS FOR CHAPTERS ===
    
    def action_view_memberships(self):
        """View all memberships for this partner - ENHANCED for chapters"""
        self.ensure_one()
        
        return {
            'name': _('Memberships: %s') % (self.name or 'Partner'),
            'type': 'ir.actions.act_window',
            'res_model': 'ams.membership',
            'view_mode': 'list,form',
            'domain': [('partner_id', '=', self.id)],
            'context': {
                'default_partner_id': self.id,
                'search_default_group_membership_type': 1,  # Group by regular vs chapter
            }
        }
    
    def action_view_chapter_memberships(self):
        """View chapter memberships only - NEW METHOD"""
        self.ensure_one()
        
        return {
            'name': _('Chapter Memberships: %s') % (self.name or 'Partner'),
            'type': 'ir.actions.act_window',
            'res_model': 'ams.membership',
            'view_mode': 'kanban,list,form',
            'domain': [('partner_id', '=', self.id), ('is_chapter_membership', '=', True)],
            'context': {
                'default_partner_id': self.id,
                'search_default_active': 1,
                'search_default_group_chapter_type': 1,
            }
        }
    
    def action_view_regular_memberships(self):
        """View regular memberships only - NEW METHOD"""
        self.ensure_one()
        
        return {
            'name': _('Regular Memberships: %s') % (self.name or 'Partner'),
            'type': 'ir.actions.act_window',
            'res_model': 'ams.membership',
            'view_mode': 'list,form',
            'domain': [('partner_id', '=', self.id), ('is_chapter_membership', '=', False)],
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
        """View active memberships for this partner - ENHANCED for chapters"""
        self.ensure_one()
        
        return {
            'name': _('Active Memberships: %s') % (self.name or 'Partner'),
            'type': 'ir.actions.act_window',
            'res_model': 'ams.membership',
            'view_mode': 'kanban,list,form',
            'domain': [('partner_id', '=', self.id), ('state', '=', 'active')],
            'context': {
                'default_partner_id': self.id,
                'search_default_group_membership_type': 1,
            }
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
        """View renewal history for this partner - ENHANCED for chapters"""
        self.ensure_one()
        
        return {
            'name': _('Renewals: %s') % (self.name or 'Partner'),
            'type': 'ir.actions.act_window',
            'res_model': 'ams.renewal',
            'view_mode': 'list,form',
            'domain': [('partner_id', '=', self.id)],
            'context': {
                'default_partner_id': self.id,
                'search_default_this_year': 1,
            }
        }
    
    def action_view_chapter_renewals(self):
        """View chapter renewals only - NEW METHOD"""
        self.ensure_one()
        
        return {
            'name': _('Chapter Renewals: %s') % (self.name or 'Partner'),
            'type': 'ir.actions.act_window',
            'res_model': 'ams.renewal',
            'view_mode': 'list,form',
            'domain': [
                ('partner_id', '=', self.id),
                ('membership_id.is_chapter_membership', '=', True)
            ],
            'context': {
                'default_partner_id': self.id,
                'search_default_this_year': 1,
            }
        }
    
    def action_view_benefits(self):
        """View active benefits for this partner - ENHANCED for chapters"""
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
            'view_mode': 'kanban,list,form',
            'domain': [('id', 'in', benefit_ids)],
            'context': {'search_default_group_applies_to': 1}
        }
    
    def action_view_chapter_benefits(self):
        """View chapter benefits only - NEW METHOD"""
        self.ensure_one()
        
        benefit_ids = []
        try:
            benefit_ids = self.chapter_benefit_ids.ids
        except Exception:
            benefit_ids = []
        
        return {
            'name': _('Chapter Benefits: %s') % (self.name or 'Partner'),
            'type': 'ir.actions.act_window',
            'res_model': 'ams.benefit',
            'view_mode': 'kanban,list,form',
            'domain': [('id', 'in', benefit_ids)],
        }

    # === CHAPTER ANALYTICS METHODS ===
    
    def get_chapter_summary(self):
        """Get summary of chapter memberships - NEW METHOD"""
        self.ensure_one()
        
        try:
            active_chapters = self.active_chapter_memberships
            if not active_chapters:
                return "No active chapter memberships"
            
            summary_parts = []
            
            # Count by type
            local_count = len(active_chapters.filtered(lambda m: m.chapter_type == 'local'))
            regional_count = len(active_chapters.filtered(lambda m: m.chapter_type == 'regional'))
            special_count = len(active_chapters.filtered(lambda m: m.chapter_type == 'special'))
            
            if local_count:
                summary_parts.append(f"{local_count} Local")
            if regional_count:
                summary_parts.append(f"{regional_count} Regional")
            if special_count:
                summary_parts.append(f"{special_count} Special Interest")
            
            # Leadership roles
            if self.chapter_leadership_roles:
                summary_parts.append(f"{self.chapter_leadership_roles} Leadership Role(s)")
            
            return "; ".join(summary_parts) if summary_parts else f"{len(active_chapters)} Active Chapter(s)"
            
        except Exception as e:
            _logger.error(f"Error getting chapter summary for {self.name}: {e}")
            return "Chapter data unavailable"
    
    def get_chapter_engagement_level(self):
        """Get chapter engagement level description - NEW METHOD"""
        self.ensure_one()
        
        score = self.chapter_engagement_score
        if score >= 80:
            return "Highly Engaged"
        elif score >= 60:
            return "Well Engaged"
        elif score >= 40:
            return "Moderately Engaged"
        elif score >= 20:
            return "Somewhat Engaged"
        elif score > 0:
            return "Minimally Engaged"
        else:
            return "No Engagement Data"

    # === BENEFIT MANAGEMENT - ENHANCED FOR CHAPTERS ===
    
    def has_benefit(self, benefit_code):
        """Check if member has a specific benefit - SAFE VERSION"""
        self.ensure_one()
        try:
            return any(benefit.code == benefit_code for benefit in self.active_benefit_ids)
        except Exception:
            return False
    
    def has_chapter_benefit(self, benefit_code):
        """Check if member has a chapter-specific benefit - NEW METHOD"""
        self.ensure_one()
        try:
            return any(benefit.code == benefit_code for benefit in self.chapter_benefit_ids)
        except Exception:
            return False
    
    def get_discount_amount(self, original_amount, benefit_codes=None):
        """Calculate total discount amount from active benefits - ENHANCED for chapter benefits"""
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
    
    def get_chapter_discount_amount(self, original_amount, benefit_codes=None):
        """Calculate discount from chapter benefits only - NEW METHOD"""
        self.ensure_one()
        
        if not original_amount:
            return 0.0
            
        total_discount = 0.0
        
        try:
            for benefit in self.chapter_benefit_ids:
                try:
                    if benefit.benefit_type != 'discount':
                        continue
                    
                    # Filter by benefit codes if specified
                    if benefit_codes and benefit.code not in benefit_codes:
                        continue
                    
                    discount = benefit.get_discount_amount(original_amount)
                    total_discount += discount
                except Exception as e:
                    _logger.warning(f"Error calculating chapter discount for benefit {benefit.id}: {e}")
                    continue
                    
        except Exception as e:
            _logger.error(f"Error getting chapter discount amount for {self.name}: {e}")
        
        return min(total_discount, original_amount)
    
    def record_benefit_usage(self, benefit_code, quantity=1, notes=None, membership_id=None):
        """Record usage of a specific benefit - ENHANCED with membership context"""
        self.ensure_one()
        
        try:
            benefit = self.active_benefit_ids.filtered(lambda b: b.code == benefit_code)
            if not benefit:
                raise UserError(_("Benefit '%s' not available for this member.") % benefit_code)
            
            return benefit[0].record_usage(self.id, quantity, notes, membership_id)
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

    # === ENHANCED CONSTRAINTS FOR CHAPTERS ===
    
    @api.constrains('membership_ids')
    def _check_single_active_regular_membership(self):
        """Ensure only one active REGULAR membership per member - ENHANCED for chapters"""
        for partner in self:
            try:
                # Only check regular memberships (chapters are unlimited)
                active_regular_memberships = partner.membership_ids.filtered(
                    lambda m: m.state == 'active' and not m.is_chapter_membership
                )
                if len(active_regular_memberships) > 1:
                    raise ValidationError(
                        _("Member %s has multiple active regular memberships. "
                          "Only one active regular membership is allowed per member. "
                          "Chapter memberships are unlimited.") % 
                        (partner.name or 'Unknown Partner')
                    )
            except Exception as e:
                _logger.error(f"Error checking single active membership constraint: {e}")

    # === CHAPTER MANAGEMENT UTILITIES ===
    
    def can_join_chapter(self, chapter_product):
        """Check if member can join a specific chapter - NEW METHOD"""
        self.ensure_one()
        
        if not self.is_member:
            return False, "Not a member"
        
        # Check if already in this chapter
        existing = self.membership_ids.filtered(
            lambda m: (m.product_id.product_tmpl_id == chapter_product and 
                      m.state in ['active', 'grace'])
        )
        if existing:
            return False, "Already a member of this chapter"
        
        # Check geographic restrictions
        if chapter_product.chapter_geographic_restriction:
            if (self.country_id != chapter_product.chapter_country_id or 
                self.state_id.name != chapter_product.chapter_state):
                return False, "Geographic restriction - not in chapter area"
        
        # Check member limits
        if (chapter_product.chapter_member_limit > 0 and 
            chapter_product.chapter_member_count >= chapter_product.chapter_member_limit):
            return False, "Chapter is at member capacity"
        
        return True, "Can join chapter"
    
    def get_recommended_chapters(self, limit=5):
        """Get recommended chapters for this member - NEW METHOD"""
        self.ensure_one()
        
        if not self.is_member:
            return self.env['product.template']
        
        # Get available chapter products
        domain = [
            ('is_chapter_product', '=', True),
            ('chapter_status', '=', 'active'),
        ]
        
        # Geographic preference
        if self.country_id:
            domain.append(('chapter_country_id', '=', self.country_id.id))
        if self.state_id:
            domain.append(('chapter_state', '=', self.state_id.name))
        
        recommended = self.env['product.template'].search(domain, limit=limit)
        
        # Filter out chapters already joined
        current_chapters = self.membership_ids.filtered(
            lambda m: m.is_chapter_membership and m.state in ['active', 'grace']
        ).mapped('product_id.product_tmpl_id')
        
        return recommended - current_chapters