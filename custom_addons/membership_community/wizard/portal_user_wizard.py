# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
import logging

_logger = logging.getLogger(__name__)


class PortalUserWizard(models.TransientModel):
    _name = 'ams.portal.user.wizard'
    _description = 'Create Portal Users for Members'

    # Selection Criteria
    member_type_ids = fields.Many2many('ams.member.type', string='Member Types',
                                     help="Leave empty to include all member types")
    member_status = fields.Selection([
        ('all', 'All Members'),
        ('active', 'Active Members Only'),
        ('active_grace', 'Active and Grace Period'),
        ('prospective', 'Prospective Members Only')
    ], string='Member Status', default='active_grace', required=True)
    
    include_existing_users = fields.Boolean('Include Members with Existing Portal Users', 
                                          default=False,
                                          help="Include members who already have portal users")
    email_required = fields.Boolean('Email Required', default=True,
                                  help="Only include members with email addresses")
    
    # Date Filters
    membership_start_after = fields.Date('Membership Start After',
                                       help="Only include members who joined after this date")
    membership_start_before = fields.Date('Membership Start Before',
                                        help="Only include members who joined before this date")
    
    # Action Options
    send_invitation_emails = fields.Boolean('Send Invitation Emails', default=True,
                                          help="Send portal invitation emails to new users")
    reset_existing_passwords = fields.Boolean('Reset Existing User Passwords', default=False,
                                            help="Reset passwords for existing portal users")
    update_user_groups = fields.Boolean('Update User Groups', default=True,
                                      help="Ensure users have correct member and portal groups")
    
    # Results and Statistics
    eligible_member_count = fields.Integer('Eligible Members', compute='_compute_eligible_members')
    preview_member_ids = fields.Many2many('res.partner', string='Preview Members',
                                        compute='_compute_eligible_members')
    
    # Processing Results
    created_user_count = fields.Integer('Created Users', readonly=True, default=0)
    updated_user_count = fields.Integer('Updated Users', readonly=True, default=0)
    error_count = fields.Integer('Errors', readonly=True, default=0)
    processing_log = fields.Text('Processing Log', readonly=True)

    @api.depends('member_type_ids', 'member_status', 'include_existing_users', 'email_required',
                 'membership_start_after', 'membership_start_before')
    def _compute_eligible_members(self):
        """Compute eligible members based on criteria"""
        for wizard in self:
            domain = [('is_member', '=', True)]
            
            # Member type filter
            if wizard.member_type_ids:
                domain.append(('member_type_id', 'in', wizard.member_type_ids.ids))
            
            # Member status filter
            if wizard.member_status == 'active':
                domain.append(('member_status', '=', 'active'))
            elif wizard.member_status == 'active_grace':
                domain.append(('member_status', 'in', ['active', 'grace']))
            elif wizard.member_status == 'prospective':
                domain.append(('member_status', '=', 'prospective'))
            # 'all' adds no filter
            
            # Email requirement
            if wizard.email_required:
                domain.append(('email', '!=', False))
                domain.append(('email', '!=', ''))
            
            # Date filters
            if wizard.membership_start_after:
                domain.append(('membership_start_date', '>=', wizard.membership_start_after))
            if wizard.membership_start_before:
                domain.append(('membership_start_date', '<=', wizard.membership_start_before))
            
            # Existing portal users
            if not wizard.include_existing_users:
                domain.append(('portal_user_id', '=', False))
            
            eligible_members = self.env['res.partner'].search(domain)
            wizard.eligible_member_count = len(eligible_members)
            wizard.preview_member_ids = [(6, 0, eligible_members.ids)]

    def action_preview_members(self):
        """Open preview of eligible members"""
        self.ensure_one()
        return {
            'name': _('Eligible Members Preview'),
            'type': 'ir.actions.act_window',
            'res_model': 'res.partner',
            'view_mode': 'list,form',
            'domain': [('id', 'in', self.preview_member_ids.ids)],
            'context': {
                'search_default_group_member_type': 1,
            },
            'target': 'new',
        }

    def action_create_portal_users(self):
        """Create portal users for eligible members"""
        self.ensure_one()
        
        if self.eligible_member_count == 0:
            raise UserError(_("No eligible members found with the current criteria."))
        
        # Get member and portal groups
        try:
            member_group = self.env.ref('membership_community.group_membership_user')
            portal_group = self.env.ref('base.group_portal')
        except ValueError as e:
            raise UserError(_("Required security groups not found: %s") % str(e))
        
        # Initialize counters and log
        created_count = 0
        updated_count = 0
        error_count = 0
        log_entries = []
        
        log_entries.append(_("Starting portal user creation process..."))
        log_entries.append(_("Eligible members: %d") % self.eligible_member_count)
        log_entries.append("-" * 50)
        
        # Process each eligible member
        for member in self.preview_member_ids:
            try:
                result = self._process_member_portal_user(
                    member, member_group, portal_group, log_entries
                )
                
                if result == 'created':
                    created_count += 1
                elif result == 'updated':
                    updated_count += 1
                    
            except Exception as e:
                error_count += 1
                error_msg = _("Error processing %s: %s") % (member.name, str(e))
                log_entries.append(error_msg)
                _logger.error(error_msg)
                continue
        
        # Update wizard with results
        log_entries.append("-" * 50)
        log_entries.append(_("Process completed:"))
        log_entries.append(_("- Created users: %d") % created_count)
        log_entries.append(_("- Updated users: %d") % updated_count)
        log_entries.append(_("- Errors: %d") % error_count)
        
        self.write({
            'created_user_count': created_count,
            'updated_user_count': updated_count,
            'error_count': error_count,
            'processing_log': '\n'.join(log_entries)
        })
        
        # Show results
        return self._show_results()

    def _process_member_portal_user(self, member, member_group, portal_group, log_entries):
        """Process portal user creation/update for a single member"""
        
        if not member.email:
            log_entries.append(_("Skipped %s: No email address") % member.name)
            return 'skipped'
        
        # Check if user already exists
        existing_user = self.env['res.users'].search([('login', '=', member.email)], limit=1)
        
        if existing_user:
            # User exists - update if needed
            if existing_user.partner_id.id != member.id:
                if existing_user.partner_id and existing_user.partner_id.id != member.id:
                    log_entries.append(
                        _("Skipped %s: Email already used by %s") % (member.name, existing_user.partner_id.name)
                    )
                    return 'skipped'
                else:
                    existing_user.partner_id = member.id
            
            # Update groups if requested
            if self.update_user_groups:
                existing_user.groups_id = [(4, member_group.id), (4, portal_group.id)]
            
            # Link to member if not already linked
            if not member.portal_user_id:
                member.write({
                    'portal_user_id': existing_user.id,
                    'portal_user_created': fields.Datetime.now()
                })
            
            # Reset password if requested
            if self.reset_existing_passwords:
                if self.send_invitation_emails:
                    existing_user.action_reset_password()
                    log_entries.append(_("Updated %s: Password reset email sent") % member.name)
                else:
                    log_entries.append(_("Updated %s: Groups updated") % member.name)
            else:
                log_entries.append(_("Updated %s: Linked existing user") % member.name)
            
            return 'updated'
            
        else:
            # Create new user
            user_vals = {
                'name': member.name,
                'login': member.email,
                'email': member.email,
                'partner_id': member.id,
                'groups_id': [(4, member_group.id), (4, portal_group.id)],
                'active': True
            }
            
            new_user = self.env['res.users'].create(user_vals)
            
            # Update member record
            member.write({
                'portal_user_id': new_user.id,
                'portal_user_created': fields.Datetime.now()
            })
            
            # Send invitation email if requested
            if self.send_invitation_emails:
                try:
                    new_user.action_reset_password()
                    log_entries.append(_("Created %s: Invitation email sent") % member.name)
                except Exception as e:
                    log_entries.append(
                        _("Created %s: User created but invitation email failed: %s") % (member.name, str(e))
                    )
            else:
                log_entries.append(_("Created %s: User created (no email sent)") % member.name)
            
            return 'created'

    def _show_results(self):
        """Show processing results"""
        self.ensure_one()
        
        return {
            'name': _('Portal User Creation Results'),
            'type': 'ir.actions.act_window',
            'res_model': 'ams.portal.user.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'view_id': self.env.ref('membership_community.view_portal_user_wizard_results').id,
            'target': 'new',
        }

    def action_download_log(self):
        """Download processing log as text file"""
        self.ensure_one()
        
        if not self.processing_log:
            raise UserError(_("No processing log available."))
        
        # Create attachment
        filename = f"portal_user_creation_log_{fields.Date.today()}.txt"
        attachment = self.env['ir.attachment'].create({
            'name': filename,
            'datas': self.processing_log.encode('utf-8'),
            'res_model': 'ams.portal.user.wizard',
            'res_id': self.id,
            'type': 'binary',
            'mimetype': 'text/plain'
        })
        
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'new'
        }

    def action_close(self):
        """Close wizard"""
        return {'type': 'ir.actions.act_window_close'}

    # Constraints and Validations
    @api.constrains('membership_start_after', 'membership_start_before')
    def _check_date_range(self):
        """Validate date range"""
        for wizard in self:
            if wizard.membership_start_after and wizard.membership_start_before:
                if wizard.membership_start_after >= wizard.membership_start_before:
                    raise ValidationError(_("'After' date must be before 'Before' date."))

    @api.onchange('member_status')
    def _onchange_member_status(self):
        """Update help text based on member status selection"""
        if self.member_status == 'prospective':
            return {
                'warning': {
                    'title': _('Prospective Members'),
                    'message': _('Creating portal users for prospective members will give them access before their membership is activated.')
                }
            }

    @api.onchange('reset_existing_passwords')
    def _onchange_reset_passwords(self):
        """Warn about password reset"""
        if self.reset_existing_passwords:
            return {
                'warning': {
                    'title': _('Password Reset'),
                    'message': _('This will reset passwords for existing portal users and send them new invitation emails.')
                }
            }


class PortalUserWizardResults(models.TransientModel):
    _name = 'ams.portal.user.wizard.results'
    _description = 'Portal User Creation Results View'

    wizard_id = fields.Many2one('ams.portal.user.wizard', 'Wizard', required=True)
    created_user_count = fields.Integer(related='wizard_id.created_user_count', readonly=True)
    updated_user_count = fields.Integer(related='wizard_id.updated_user_count', readonly=True)
    error_count = fields.Integer(related='wizard_id.error_count', readonly=True)
    processing_log = fields.Text(related='wizard_id.processing_log', readonly=True)