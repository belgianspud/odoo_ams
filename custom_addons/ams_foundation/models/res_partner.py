# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from datetime import date, datetime, timedelta
import logging

_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _inherit = 'res.partner'

    # Core Member Fields
    is_member = fields.Boolean('Is Association Member', default=False, tracking=True)
    member_number = fields.Char('Member ID', readonly=True, copy=False, tracking=True)
    member_type_id = fields.Many2one('ams.member.type', 'Member Type', tracking=True)
    member_status = fields.Selection([
        ('prospective', 'Prospective'),
        ('active', 'Active'),
        ('grace', 'Grace Period'),
        ('lapsed', 'Lapsed'),
        ('suspended', 'Suspended'),
        ('terminated', 'Terminated')
    ], string='Member Status', default='prospective', tracking=True)

    # Membership Timeline
    membership_start_date = fields.Date('Membership Start', tracking=True)
    membership_end_date = fields.Date('Membership End', tracking=True)
    last_renewal_date = fields.Date('Last Renewal')
    grace_period_end = fields.Date('Grace Period End', readonly=True)
    suspend_end_date = fields.Date('Suspend End Date', readonly=True)
    terminate_date = fields.Date('Terminate Date', readonly=True)

    # Professional Information
    professional_designation = fields.Char('Professional Designation')
    license_number = fields.Char('License Number')
    specialty_area = fields.Char('Specialty/Focus Area')
    years_experience = fields.Integer('Years of Experience')
    employer_name = fields.Char('Current Employer')
    job_title = fields.Char('Job Title')

    # Communication Preferences
    communication_preferences = fields.Selection([
        ('email', 'Email Only'),
        ('mail', 'Physical Mail Only'),
        ('both', 'Email and Mail'),
        ('minimal', 'Minimal Contact')
    ], string='Communication Preference', default='email')
    newsletter_subscription = fields.Boolean('Newsletter Subscription', default=True)
    directory_listing = fields.Boolean('Include in Member Directory', default=True)
    preferred_language = fields.Many2one('res.lang', 'Preferred Language')

    # Engagement and Analytics
    engagement_score = fields.Float('Engagement Score', readonly=True, default=0.0)
    last_portal_login = fields.Datetime('Last Portal Login', readonly=True)
    portal_login_count = fields.Integer('Portal Login Count', readonly=True, default=0)

    # Member Management
    membership_notes = fields.Text('Membership Notes')
    status_change_reason = fields.Text('Status Change Reason')
    last_status_change = fields.Datetime('Last Status Change', readonly=True)
    auto_status_enabled = fields.Boolean('Auto Status Transitions', default=True)

    # Portal User Management
    portal_user_id = fields.Many2one('res.users', 'Portal User', readonly=True)
    portal_user_created = fields.Datetime('Portal User Created', readonly=True)

    # Integration with membership_community
    membership_ids = fields.One2many(
        'membership.membership', 
        'partner_id', 
        string='Membership Records',
        help="All membership records for this member"
    )
    current_membership_id = fields.Many2one(
        'membership.membership', 
        string='Current Membership Record',
        compute='_compute_current_membership', 
        store=True,
        help="The currently active membership record"
    )
    membership_record_count = fields.Integer(
        'Membership Count', 
        compute='_compute_membership_record_count',
        help="Total number of membership records"
    )

    @api.model
    def create(self, vals):
        """Override create to handle member creation logic"""
        partner = super().create(vals)
        
        # Generate member number if is_member is True and no number exists
        if partner.is_member and not partner.member_number:
            partner._generate_member_number()
        
        # Create portal user if auto-creation is enabled (but avoid recursion)
        if partner.is_member and not partner.portal_user_id:
            partner._try_auto_create_portal_user()
        
        return partner

    def write(self, vals):
        """Override write to handle member updates"""
        # Prevent infinite recursion by tracking if we're already processing portal user creation
        context = self.env.context or {}
        if context.get('skip_portal_creation'):
            return super().write(vals)

        # Handle is_member status changes
        if 'is_member' in vals:
            for partner in self:
                if vals['is_member'] and not partner.member_number:
                    # Becoming a member - generate member number
                    partner._generate_member_number()
                elif not vals['is_member'] and partner.is_member:
                    # No longer a member - handle cleanup
                    partner._handle_member_deactivation()

        # Track status changes
        if 'member_status' in vals and vals['member_status']:
            vals['last_status_change'] = fields.Datetime.now()

        result = super().write(vals)

        # Handle post-write actions for members (avoid recursion)
        if not context.get('skip_portal_creation'):
            for partner in self:
                if partner.is_member:
                    if 'member_status' in vals:
                        partner._handle_status_change(vals['member_status'])
                    
                    # Auto-create portal user if needed (avoid recursion)
                    if not partner.portal_user_id and partner.email:
                        partner._try_auto_create_portal_user()

        return result

    def _generate_member_number(self):
        """Generate sequential member number"""
        self.ensure_one()
        if not self.member_number:
            sequence = self.env['ir.sequence'].next_by_code('ams.member.number')
            self.member_number = sequence

    def _try_auto_create_portal_user(self):
        """Try to automatically create portal user with better error handling"""
        self.ensure_one()
        
        # Skip if already has portal user or no email
        if self.portal_user_id or not self.email:
            return
        
        # Check settings
        settings = self._get_ams_settings()
        if not settings or not settings.auto_create_portal_users:
            return
        
        try:
            # Use context to prevent recursion
            self.with_context(skip_portal_creation=True).action_create_portal_user()
        except Exception as e:
            # Log the error but don't raise it to prevent blocking other operations
            _logger.warning(f"Failed to auto-create portal user for {self.name}: {str(e)}")

    def _handle_member_deactivation(self):
        """Handle cleanup when member is deactivated"""
        self.ensure_one()
        self.with_context(skip_portal_creation=True).write({
            'member_status': 'terminated',
            'membership_end_date': fields.Date.today(),
            'auto_status_enabled': False
        })

    def _handle_status_change(self, new_status):
        """Handle automatic date calculations on status change"""
        self.ensure_one()
        settings = self._get_ams_settings()
        if not settings:
            return

        today = fields.Date.today()
        update_vals = {}
        
        if new_status == 'grace':
            update_vals['grace_period_end'] = today + timedelta(days=settings.grace_period_days)
        elif new_status == 'suspended':
            update_vals['suspend_end_date'] = today + timedelta(days=settings.suspend_period_days)
        elif new_status == 'terminated':
            update_vals['terminate_date'] = today + timedelta(days=settings.terminate_period_days)
        
        if update_vals:
            self.with_context(skip_portal_creation=True).write(update_vals)

    def _get_ams_settings(self):
        """Get active AMS settings"""
        return self.env['ams.settings'].search([('active', '=', True)], limit=1)

    @api.depends('membership_ids', 'membership_ids.state', 'membership_ids.start_date')
    def _compute_current_membership(self):
        """Get the current active membership record"""
        for partner in self:
            # First try to find active memberships
            active_memberships = partner.membership_ids.filtered(
                lambda m: m.state == 'active'
            ).sorted('start_date', reverse=True)
            
            if active_memberships:
                partner.current_membership_id = active_memberships[0]
            else:
                # If no active, get the most recent one
                recent = partner.membership_ids.sorted('start_date', reverse=True)
                partner.current_membership_id = recent[0] if recent else False

    @api.depends('membership_ids')
    def _compute_membership_record_count(self):
        """Count total membership records"""
        for partner in self:
            partner.membership_record_count = len(partner.membership_ids)

    def action_view_membership_records(self):
        """Open list of all membership records for this partner"""
        self.ensure_one()
        
        return {
            'name': _('Membership Records: %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'membership.membership',
            'view_mode': 'list,form',
            'domain': [('partner_id', '=', self.id)],
            'context': {
                'default_partner_id': self.id,
                'default_membership_type_id': self.member_type_id.id if self.member_type_id else False,
            },
            'target': 'current',
        }

    def action_create_membership_record(self):
        """Create a new membership record for this partner"""
        self.ensure_one()
        
        # Check if member type is set
        if not self.member_type_id:
            raise UserError(_("Please set a member type before creating a membership record."))
        
        # Check if partner is marked as member
        if not self.is_member:
            raise UserError(_("Partner must be marked as 'Is Association Member' before creating membership records."))
        
        return {
            'name': _('New Membership Record'),
            'type': 'ir.actions.act_window',
            'res_model': 'membership.membership',
            'view_mode': 'form',
            'context': {
                'default_partner_id': self.id,
                'default_membership_type_id': self.member_type_id.id,
                'default_start_date': fields.Date.today(),
            },
            'target': 'current',
        }

    # Status Action Methods
    def action_activate_member(self):
        """Activate prospective member"""
        for partner in self:
            if partner.member_status != 'prospective':
                raise UserError(_("Only prospective members can be activated."))
            
            partner.write({
                'member_status': 'active',
                'membership_start_date': fields.Date.today(),
                'status_change_reason': 'Manual activation by staff'
            })
            
            # Set membership end date based on member type
            if partner.member_type_id and partner.member_type_id.membership_duration:
                end_date = fields.Date.today() + timedelta(days=partner.member_type_id.membership_duration)
                partner.with_context(skip_portal_creation=True).write({'membership_end_date': end_date})

    def action_suspend_member(self):
        """Suspend active or grace period member"""
        for partner in self:
            if partner.member_status not in ['active', 'grace']:
                raise UserError(_("Only active or grace period members can be suspended."))
            
            partner.write({
                'member_status': 'suspended',
                'status_change_reason': 'Manual suspension by staff'
            })

    def action_terminate_member(self):
        """Terminate member"""
        for partner in self:
            if partner.member_status == 'terminated':
                raise UserError(_("Member is already terminated."))
            
            partner.write({
                'member_status': 'terminated',
                'membership_end_date': fields.Date.today(),
                'status_change_reason': 'Manual termination by staff'
            })

    def action_reinstate_member(self):
        """Reinstate suspended or terminated member"""
        for partner in self:
            if partner.member_status not in ['suspended', 'terminated']:
                raise UserError(_("Only suspended or terminated members can be reinstated."))
            
            update_vals = {
                'member_status': 'active',
                'status_change_reason': 'Manual reinstatement by staff'
            }
            
            # Extend membership if needed
            if not partner.membership_end_date or partner.membership_end_date <= fields.Date.today():
                if partner.member_type_id and partner.member_type_id.membership_duration:
                    end_date = fields.Date.today() + timedelta(days=partner.member_type_id.membership_duration)
                    update_vals['membership_end_date'] = end_date
            
            partner.write(update_vals)

    # Portal User Management
    def action_create_portal_user(self):
        """Create portal user for member"""
        for partner in self:
            if partner.portal_user_id:
                raise UserError(_("Portal user already exists for this member."))
            
            if not partner.email:
                raise UserError(_("Member must have an email address to create portal user."))
            
            # Check if user with this email already exists
            existing_user = self.env['res.users'].search([('login', '=', partner.email)], limit=1)
            if existing_user:
                # Link existing user if they don't have a partner or link to this partner
                if not existing_user.partner_id or existing_user.partner_id.id == partner.id:
                    # Update existing user
                    existing_user.partner_id = partner.id
                    
                    # Add member and portal groups
                    try:
                        member_group = self.env.ref('ams_foundation.group_ams_member')
                        portal_group = self.env.ref('base.group_portal')
                        existing_user.groups_id = [(4, member_group.id), (4, portal_group.id)]
                    except Exception as e:
                        _logger.warning(f"Could not add groups to existing user: {str(e)}")
                    
                    partner.with_context(skip_portal_creation=True).write({
                        'portal_user_id': existing_user.id,
                        'portal_user_created': fields.Datetime.now()
                    })
                else:
                    raise UserError(_("A user with this email already exists and is linked to another partner."))
            else:
                # Create new portal user
                try:
                    member_group = self.env.ref('ams_foundation.group_ams_member')
                    portal_group = self.env.ref('base.group_portal')
                except Exception as e:
                    raise UserError(_("Required security groups not found: %s") % str(e))
                
                user_vals = {
                    'name': partner.name,
                    'login': partner.email,
                    'email': partner.email,
                    'partner_id': partner.id,
                    'groups_id': [(4, member_group.id), (4, portal_group.id)],
                    'active': True
                }
                
                try:
                    user = self.env['res.users'].create(user_vals)
                    partner.with_context(skip_portal_creation=True).write({
                        'portal_user_id': user.id,
                        'portal_user_created': fields.Datetime.now()
                    })
                    
                    # Send invitation email
                    try:
                        user.action_reset_password()
                    except Exception as e:
                        _logger.warning(f"Failed to send portal invitation to {partner.email}: {str(e)}")
                        
                except Exception as e:
                    raise UserError(_("Failed to create portal user: %s") % str(e))

    def action_reset_portal_password(self):
        """Reset portal user password"""
        for partner in self:
            if not partner.portal_user_id:
                raise UserError(_("No portal user exists for this member."))
            
            try:
                partner.portal_user_id.action_reset_password()
            except Exception as e:
                raise UserError(_("Failed to reset password: %s") % str(e))

    # Cron Job Methods
    @api.model
    def process_member_status_transitions(self):
        """Cron job to process automated member status transitions"""
        _logger.info("Starting member status transitions processing...")
        
        settings = self.env['ams.settings'].search([('active', '=', True)], limit=1)
        if not settings or not settings.auto_status_transitions:
            _logger.info("Auto status transitions disabled, skipping...")
            return

        today = fields.Date.today()
        processed_count = 0

        try:
            # Process expired memberships -> grace period
            expired_members = self.search([
                ('is_member', '=', True),
                ('member_status', '=', 'active'),
                ('membership_end_date', '<=', today),
                ('auto_status_enabled', '=', True)
            ])
            
            for member in expired_members:
                member.with_context(skip_portal_creation=True).write({
                    'member_status': 'grace',
                    'status_change_reason': 'Automatic transition: membership expired'
                })
                processed_count += 1
            
            _logger.info(f"Moved {len(expired_members)} members to grace period")

            # Process grace period -> lapsed
            grace_expired = self.search([
                ('is_member', '=', True),
                ('member_status', '=', 'grace'),
                ('grace_period_end', '<=', today),
                ('auto_status_enabled', '=', True)
            ])
            
            for member in grace_expired:
                member.with_context(skip_portal_creation=True).write({
                    'member_status': 'lapsed',
                    'status_change_reason': 'Automatic transition: grace period expired'
                })
                processed_count += 1
            
            _logger.info(f"Moved {len(grace_expired)} members to lapsed status")

            # Process suspended -> lapsed (if suspend period ended)
            suspend_expired = self.search([
                ('is_member', '=', True),
                ('member_status', '=', 'suspended'),
                ('suspend_end_date', '<=', today),
                ('auto_status_enabled', '=', True)
            ])
            
            for member in suspend_expired:
                member.with_context(skip_portal_creation=True).write({
                    'member_status': 'lapsed',
                    'status_change_reason': 'Automatic transition: suspension period expired'
                })
                processed_count += 1
            
            _logger.info(f"Moved {len(suspend_expired)} suspended members to lapsed")

            _logger.info(f"Status transitions completed. Total processed: {processed_count}")

        except Exception as e:
            _logger.error(f"Error in member status transitions: {str(e)}")

    @api.model
    def recalculate_engagement_scores(self):
        """Cron job to recalculate member engagement scores"""
        _logger.info("Starting engagement score recalculation...")
        
        settings = self.env['ams.settings'].search([('active', '=', True)], limit=1)
        if not settings or not settings.engagement_scoring_enabled:
            _logger.info("Engagement scoring disabled, skipping...")
            return

        try:
            active_members = self.search([
                ('is_member', '=', True),
                ('member_status', '=', 'active')
            ])
            
            for member in active_members:
                # Placeholder for engagement score calculation
                # Will be implemented in future modules
                new_score = settings.default_engagement_score
                member.with_context(skip_portal_creation=True).write({'engagement_score': new_score})
            
            _logger.info(f"Recalculated engagement scores for {len(active_members)} members")

        except Exception as e:
            _logger.error(f"Error in engagement score recalculation: {str(e)}")

    @api.model
    def create_missing_portal_users(self):
        """Cron job to create portal users for members without them"""
        _logger.info("Starting portal user creation for members...")
        
        settings = self.env['ams.settings'].search([('active', '=', True)], limit=1)
        if not settings or not settings.auto_create_portal_users:
            _logger.info("Auto portal user creation disabled, skipping...")
            return

        try:
            members_without_portal = self.search([
                ('is_member', '=', True),
                ('member_status', 'in', ['active', 'grace']),
                ('portal_user_id', '=', False),
                ('email', '!=', False)
            ])
            
            created_count = 0
            for member in members_without_portal:
                try:
                    member.action_create_portal_user()
                    created_count += 1
                except Exception as e:
                    _logger.warning(f"Failed to create portal user for {member.name}: {str(e)}")
                    continue
            
            _logger.info(f"Created {created_count} portal users")

        except Exception as e:
            _logger.error(f"Error in portal user creation: {str(e)}")

    @api.model
    def assign_missing_member_numbers(self):
        """Cron job to assign member numbers to members without them"""
        _logger.info("Starting member number assignment...")
        
        try:
            members_without_numbers = self.search([
                ('is_member', '=', True),
                ('member_number', '=', False)
            ])
            
            for member in members_without_numbers:
                member._generate_member_number()
            
            _logger.info(f"Assigned member numbers to {len(members_without_numbers)} members")

        except Exception as e:
            _logger.error(f"Error in member number assignment: {str(e)}")

    # Constraints and Validations
    @api.constrains('membership_start_date', 'membership_end_date')
    def _check_membership_dates(self):
        """Validate membership dates"""
        for partner in self:
            if partner.membership_start_date and partner.membership_end_date:
                if partner.membership_end_date <= partner.membership_start_date:
                    raise ValidationError(_("Membership end date must be after start date."))

    @api.constrains('is_member', 'member_type_id')
    def _check_member_type_required(self):
        """Ensure member type is set for members"""
        for partner in self:
            if partner.is_member and not partner.member_type_id:
                raise ValidationError(_("Member type is required for association members."))

    @api.constrains('years_experience')
    def _check_years_experience(self):
        """Validate years of experience"""
        for partner in self:
            if partner.years_experience and partner.years_experience < 0:
                raise ValidationError(_("Years of experience cannot be negative."))
            if partner.years_experience and partner.years_experience > 100:
                raise ValidationError(_("Years of experience seems unrealistic (>100 years)."))