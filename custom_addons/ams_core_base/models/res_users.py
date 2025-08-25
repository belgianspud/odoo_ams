# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, AccessError


class ResUsers(models.Model):
    """Extend res.users to add AMS-specific roles and functionality."""
    
    _inherit = 'res.users'
    
    # === AMS Role Fields ===
    ams_role_ids = fields.Many2many(
        'ams.user.role',
        'user_ams_role_rel',
        'user_id',
        'role_id',
        string='AMS Roles',
        help='AMS-specific roles assigned to this user'
    )
    
    primary_ams_role_id = fields.Many2one(
        'ams.user.role',
        string='Primary AMS Role',
        help='Primary AMS role for this user'
    )
    
    is_ams_guest = fields.Boolean(
        string='AMS Guest',
        compute='_compute_ams_role_flags',
        store=True,
        help='User has guest access only'
    )
    
    is_ams_member = fields.Boolean(
        string='AMS Member',
        compute='_compute_ams_role_flags',
        store=True,
        help='User is an AMS member'
    )
    
    is_ams_company_poc = fields.Boolean(
        string='AMS Company POC',
        compute='_compute_ams_role_flags',
        store=True,
        help='User is a company point of contact'
    )
    
    is_ams_staff = fields.Boolean(
        string='AMS Staff',
        compute='_compute_ams_role_flags',
        store=True,
        help='User is AMS staff'
    )
    
    is_ams_admin = fields.Boolean(
        string='AMS Admin',
        compute='_compute_ams_role_flags',
        store=True,
        help='User is an AMS administrator'
    )
    
    # === Portal and Access Control ===
    ams_portal_access = fields.Boolean(
        string='AMS Portal Access',
        default=False,
        help='User has access to AMS member portal'
    )
    
    portal_access_granted_date = fields.Datetime(
        string='Portal Access Granted',
        help='When portal access was first granted'
    )
    
    last_portal_login = fields.Datetime(
        string='Last Portal Login',
        help='Last time user logged into portal'
    )
    
    # === Company Access (for Company POCs) ===
    managed_company_ids = fields.Many2many(
        'res.partner',
        'user_managed_company_rel',
        'user_id',
        'company_id',
        string='Managed Companies',
        domain="[('is_company', '=', True)]",
        help='Companies this user can manage as POC'
    )
    
    can_manage_employees = fields.Boolean(
        string='Can Manage Employees',
        default=False,
        help='POC can manage employee records for their companies'
    )
    
    can_assign_training = fields.Boolean(
        string='Can Assign Training',
        default=False,
        help='POC can assign training to employees'
    )
    
    # === Security and Audit ===
    failed_login_attempts = fields.Integer(
        string='Failed Login Attempts',
        default=0,
        help='Number of consecutive failed login attempts'
    )
    
    account_locked = fields.Boolean(
        string='Account Locked',
        default=False,
        help='Account is temporarily locked due to security'
    )
    
    locked_until = fields.Datetime(
        string='Locked Until',
        help='Account locked until this time'
    )
    
    password_reset_required = fields.Boolean(
        string='Password Reset Required',
        default=False,
        help='User must reset password on next login'
    )
    
    # === Computed Fields ===
    @api.depends('ams_role_ids', 'primary_ams_role_id')
    def _compute_ams_role_flags(self):
        """Compute boolean flags based on assigned AMS roles."""
        for user in self:
            role_codes = user.ams_role_ids.mapped('code')
            
            user.is_ams_guest = 'guest' in role_codes
            user.is_ams_member = 'member' in role_codes
            user.is_ams_company_poc = 'company_poc' in role_codes
            user.is_ams_staff = 'staff' in role_codes
            user.is_ams_admin = 'admin' in role_codes
    
    # === Role Management Methods ===
    def assign_ams_role(self, role_code, set_as_primary=False):
        """Assign an AMS role to the user."""
        self.ensure_one()
        
        role = self.env['ams.user.role'].search([
            ('code', '=', role_code),
            ('active', '=', True)
        ], limit=1)
        
        if not role:
            raise ValidationError(_('AMS role with code "%s" not found.') % role_code)
        
        # Add role if not already assigned
        if role not in self.ams_role_ids:
            self.ams_role_ids = [(4, role.id)]
        
        # Set as primary if requested
        if set_as_primary:
            self.primary_ams_role_id = role
        
        # Grant portal access for members
        if role_code in ['member', 'company_poc'] and not self.ams_portal_access:
            self.grant_portal_access()
    
    def remove_ams_role(self, role_code):
        """Remove an AMS role from the user."""
        self.ensure_one()
        
        role = self.env['ams.user.role'].search([('code', '=', role_code)], limit=1)
        if role and role in self.ams_role_ids:
            self.ams_role_ids = [(3, role.id)]
            
            # Clear primary role if it was the removed role
            if self.primary_ams_role_id == role:
                remaining_roles = self.ams_role_ids
                self.primary_ams_role_id = remaining_roles[0] if remaining_roles else False
    
    def grant_portal_access(self):
        """Grant portal access to the user."""
        self.ensure_one()
        
        if not self.ams_portal_access:
            self.write({
                'ams_portal_access': True,
                'portal_access_granted_date': fields.Datetime.now()
            })
            
            # Add to portal group
            portal_group = self.env.ref('base.group_portal', raise_if_not_found=False)
            if portal_group and portal_group not in self.groups_id:
                self.groups_id = [(4, portal_group.id)]
    
    def revoke_portal_access(self):
        """Revoke portal access from the user."""
        self.ensure_one()
        
        if self.ams_portal_access:
            self.write({
                'ams_portal_access': False,
                'portal_access_granted_date': False
            })
            
            # Remove from portal group
            portal_group = self.env.ref('base.group_portal', raise_if_not_found=False)
            if portal_group and portal_group in self.groups_id:
                self.groups_id = [(3, portal_group.id)]
    
    # === Security Methods ===
    def lock_account(self, duration_minutes=60):
        """Lock user account for security."""
        self.ensure_one()
        
        locked_until = fields.Datetime.now() + fields.Timedelta(minutes=duration_minutes)
        self.write({
            'account_locked': True,
            'locked_until': locked_until
        })
    
    def unlock_account(self):
        """Unlock user account."""
        self.ensure_one()
        
        self.write({
            'account_locked': False,
            'locked_until': False,
            'failed_login_attempts': 0
        })
    
    def increment_failed_login(self):
        """Increment failed login attempts."""
        self.ensure_one()
        
        self.failed_login_attempts += 1
        
        # Lock account after 5 failed attempts
        if self.failed_login_attempts >= 5:
            self.lock_account()
    
    def reset_failed_login(self):
        """Reset failed login attempts on successful login."""
        self.ensure_one()
        
        if self.failed_login_attempts > 0:
            self.write({
                'failed_login_attempts': 0,
                'last_portal_login': fields.Datetime.now()
            })
    
    # === Company POC Methods ===
    def add_managed_company(self, company_id):
        """Add a company to be managed by this POC."""
        self.ensure_one()
        
        if not self.is_ams_company_poc:
            raise AccessError(_('User must have Company POC role to manage companies.'))
        
        company = self.env['res.partner'].browse(company_id)
        if not company.is_company:
            raise ValidationError(_('Can only manage company records.'))
        
        if company not in self.managed_company_ids:
            self.managed_company_ids = [(4, company_id)]
    
    def remove_managed_company(self, company_id):
        """Remove a company from management."""
        self.ensure_one()
        
        self.managed_company_ids = [(3, company_id)]
    
    def get_managed_employees(self):
        """Get all employees of companies managed by this POC."""
        self.ensure_one()
        
        if not self.is_ams_company_poc:
            return self.env['res.partner'].browse([])
        
        employees = self.env['res.partner']
        for company in self.managed_company_ids:
            company_employees = company.get_employees()
            employees |= company_employees.mapped('partner_id')
        
        return employees
    
    # === Overrides ===
    @api.model_create_multi
    def create(self, vals_list):
        """Override create to handle AMS-specific setup."""
        users = super().create(vals_list)
        
        for user in users:
            # Auto-assign guest role if no AMS roles specified
            if not user.ams_role_ids:
                user.assign_ams_role('guest')
        
        return users
    
    def write(self, vals):
        """Override write to handle role changes."""
        result = super().write(vals)
        
        # Handle primary role validation
        if 'primary_ams_role_id' in vals:
            for user in self:
                if (user.primary_ams_role_id and 
                    user.primary_ams_role_id not in user.ams_role_ids):
                    raise ValidationError(_(
                        'Primary AMS role must be one of the assigned roles.'
                    ))
        
        return result


class AmsUserRole(models.Model):
    """Define AMS-specific user roles with permissions."""
    
    _name = 'ams.user.role'
    _description = 'AMS User Role'
    _order = 'sequence, name'
    
    name = fields.Char(
        string='Role Name',
        required=True,
        translate=True
    )
    
    code = fields.Char(
        string='Role Code',
        required=True,
        size=50,
        help='Technical code for this role'
    )
    
    description = fields.Text(
        string='Description',
        translate=True,
        help='Description of this role and its permissions'
    )
    
    sequence = fields.Integer(
        string='Sequence',
        default=10
    )
    
    active = fields.Boolean(
        string='Active',
        default=True
    )
    
    # Permission flags
    can_access_portal = fields.Boolean(
        string='Portal Access',
        default=False,
        help='Can access member portal'
    )
    
    can_manage_own_profile = fields.Boolean(
        string='Manage Own Profile',
        default=True,
        help='Can edit own profile information'
    )
    
    can_view_other_members = fields.Boolean(
        string='View Other Members',
        default=False,
        help='Can view other member profiles'
    )
    
    can_manage_employees = fields.Boolean(
        string='Manage Employees',
        default=False,
        help='Can manage employee records'
    )
    
    can_access_admin = fields.Boolean(
        string='Admin Access',
        default=False,
        help='Can access admin functions'
    )
    
    # Odoo groups mapping
    odoo_group_ids = fields.Many2many(
        'res.groups',
        'ams_role_group_rel',
        'role_id',
        'group_id',
        string='Odoo Groups',
        help='Odoo security groups for this role'
    )
    
    user_count = fields.Integer(
        string='Users Count',
        compute='_compute_user_count'
    )
    
    @api.depends('code')
    def _compute_user_count(self):
        """Count users with this role."""
        for role in self:
            role.user_count = self.env['res.users'].search_count([
                ('ams_role_ids', 'in', role.id)
            ])
    
    _sql_constraints = [
        ('code_unique', 'UNIQUE(code)', 'Role code must be unique.'),
    ]
    
    def assign_to_users(self, user_ids):
        """Assign this role to multiple users."""
        users = self.env['res.users'].browse(user_ids)
        for user in users:
            user.assign_ams_role(self.code)
    
    def remove_from_users(self, user_ids):
        """Remove this role from multiple users."""
        users = self.env['res.users'].browse(user_ids)
        for user in users:
            user.remove_ams_role(self.code)
    
    def action_view_users(self):
        """View users with this role."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': f'Users - {self.name}',
            'res_model': 'res.users',
            'view_mode': 'tree,form',
            'domain': [('ams_role_ids', 'in', self.id)],
            'context': {
                'search_default_ams_role_ids': self.id
            }
        }