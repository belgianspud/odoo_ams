# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class AMSMemberStatus(models.Model):
    """Member status definitions for membership lifecycle management."""
    
    _name = 'ams.member.status'
    _inherit = ['mail.thread']
    _description = 'AMS Member Status'
    _order = 'sequence, name'
    
    # ========================================================================
    # FIELDS
    # ========================================================================
    
    name = fields.Char(
        string="Status Name",
        required=True,
        help="Display name for this member status"
    )
    
    code = fields.Char(
        string="Code",
        required=True,
        help="Unique code for this member status"
    )
    
    is_active = fields.Boolean(
        string="Counts as Active Member",
        default=True,
        help="Members with this status count toward active membership statistics"
    )
    
    sequence = fields.Integer(
        string="Lifecycle Order",
        required=True,
        help="Order in the membership lifecycle (lower = earlier stage)"
    )
    
    description = fields.Text(
        string="Description",
        help="Detailed description of this member status"
    )
    
    color = fields.Integer(
        string="Kanban Color",
        default=1,
        help="Color used for visual display in kanban and calendar views"
    )
    
    can_renew = fields.Boolean(
        string="Can Renew",
        default=True,
        help="Members with this status can renew their membership"
    )
    
    can_purchase = fields.Boolean(
        string="Can Purchase Products",
        default=True,
        help="Members with this status can purchase products and services"
    )
    
    # ========================================================================
    # ADDITIONAL STATUS PROPERTIES
    # ========================================================================
    
    is_pending = fields.Boolean(
        string="Pending Status",
        default=False,
        help="This status represents a pending state requiring action"
    )
    
    is_suspended = fields.Boolean(
        string="Suspended Status",
        default=False,
        help="This status represents a suspended membership"
    )
    
    is_terminated = fields.Boolean(
        string="Terminated Status",
        default=False,
        help="This status represents a terminated membership"
    )
    
    allows_portal_access = fields.Boolean(
        string="Allows Portal Access",
        default=True,
        help="Members with this status can access the member portal"
    )
    
    requires_approval = fields.Boolean(
        string="Requires Approval",
        default=False,
        help="Transitioning to this status requires administrative approval"
    )
    
    auto_transition_days = fields.Integer(
        string="Auto-transition After (Days)",
        help="Automatically transition from this status after specified days (0 = no auto-transition)"
    )
    
    next_status_id = fields.Many2one(
        'ams.member.status',
        string="Next Status",
        help="Status to transition to after auto-transition period"
    )
    
    # ========================================================================
    # COMPUTED FIELDS
    # ========================================================================
    
    member_count = fields.Integer(
        string="Current Members",
        compute='_compute_member_count',
        help="Number of members currently in this status"
    )
    
    is_final_status = fields.Boolean(
        string="Final Status",
        compute='_compute_is_final_status',
        help="This status has no automatic transitions"
    )
    
    # ========================================================================
    # SQL CONSTRAINTS
    # ========================================================================
    
    _sql_constraints = [
        ('code_unique', 'UNIQUE(code)', 'Member status code must be unique!'),
        ('name_unique', 'UNIQUE(name)', 'Member status name must be unique!'),
        ('sequence_positive', 'CHECK(sequence > 0)', 'Sequence must be positive!'),
        ('color_range', 'CHECK(color >= 0 AND color <= 11)', 'Color must be between 0 and 11!'),
        ('auto_transition_positive', 'CHECK(auto_transition_days >= 0)', 'Auto-transition days must be positive!'),
    ]
    
    # ========================================================================
    # CONSTRAINT METHODS
    # ========================================================================
    
    @api.constrains('auto_transition_days', 'next_status_id')
    def _check_auto_transition(self):
        """Validate auto-transition configuration."""
        for record in self:
            if record.auto_transition_days > 0 and not record.next_status_id:
                raise ValidationError(_("Next status is required when auto-transition days is set"))
            if record.next_status_id and record.auto_transition_days <= 0:
                raise ValidationError(_("Auto-transition days must be greater than 0 when next status is set"))
    
    @api.constrains('next_status_id')
    def _check_circular_transition(self):
        """Prevent circular status transitions."""
        for record in self:
            if record.next_status_id:
                visited = set()
                current = record
                
                while current and current.next_status_id:
                    if current.id in visited:
                        raise ValidationError(_("Circular status transition detected: %s") % 
                                            " → ".join([s.name for s in visited]))
                    visited.add(current.id)
                    current = current.next_status_id
    
    @api.constrains('code')
    def _check_code_format(self):
        """Validate code format."""
        for record in self:
            if record.code:
                if not record.code.replace('_', '').replace('-', '').isalnum():
                    raise ValidationError(_("Code can only contain letters, numbers, underscores, and hyphens"))
                if len(record.code) > 20:
                    raise ValidationError(_("Code cannot be longer than 20 characters"))
    
    @api.constrains('is_active', 'is_suspended', 'is_terminated')
    def _check_status_consistency(self):
        """Ensure status flags are logically consistent."""
        for record in self:
            if record.is_active and (record.is_suspended or record.is_terminated):
                raise ValidationError(_("Active status cannot be suspended or terminated"))
            if record.is_suspended and record.is_terminated:
                raise ValidationError(_("Status cannot be both suspended and terminated"))
    
    # ========================================================================
    # COMPUTE METHODS
    # ========================================================================
    
    def _compute_member_count(self):
        """Compute current member count for this status."""
        # This will be implemented when member model is available
        for record in self:
            record.member_count = 0
    
    def _compute_is_final_status(self):
        """Determine if this is a final status with no transitions."""
        for record in self:
            record.is_final_status = not bool(record.auto_transition_days and record.next_status_id)
    
    # ========================================================================
    # ONCHANGE METHODS
    # ========================================================================
    
    @api.onchange('name')
    def _onchange_name(self):
        """Auto-generate code from name if code is empty."""
        if self.name and not self.code:
            # Generate code from name: "Active Member" -> "ACTIVE_MEMBER"
            self.code = self.name.upper().replace(' ', '_').replace('-', '_')
            # Remove special characters except underscores
            self.code = ''.join(c for c in self.code if c.isalnum() or c == '_')
    
    @api.onchange('is_suspended', 'is_terminated')
    def _onchange_status_flags(self):
        """Update dependent fields when status flags change."""
        if self.is_suspended or self.is_terminated:
            self.is_active = False
            self.can_renew = False
            self.allows_portal_access = False
            if self.is_terminated:
                self.can_purchase = False
    
    @api.onchange('is_active')
    def _onchange_is_active(self):
        """Update permissions when active status changes."""
        if not self.is_active:
            # Non-active members typically can't renew
            if not (self.is_pending or self.is_suspended):
                self.can_renew = False
    
    @api.onchange('is_pending')
    def _onchange_is_pending(self):
        """Update settings for pending status."""
        if self.is_pending:
            self.requires_approval = True
            self.allows_portal_access = False
    
    # ========================================================================
    # CRUD METHODS
    # ========================================================================
    
    @api.model_create_multi
    def create(self, vals_list):
        """Override create to ensure proper sequencing."""
        for vals in vals_list:
            # Set sequence if not provided
            if 'sequence' not in vals or not vals['sequence']:
                last_sequence = self.search([], order='sequence desc', limit=1).sequence or 0
                vals['sequence'] = last_sequence + 10
        
        return super().create(vals_list)
    
    def copy(self, default=None):
        """Override copy to ensure unique names and codes."""
        default = dict(default or {})
        default.update({
            'name': _("%s (Copy)") % self.name,
            'code': "%s_COPY" % self.code,
        })
        return super().copy(default)
    
    # ========================================================================
    # BUSINESS METHODS
    # ========================================================================
    
    def can_transition_to(self, target_status):
        """Check if transition to target status is allowed.
        
        Args:
            target_status (ams.member.status): Target status record
            
        Returns:
            bool: True if transition is allowed
        """
        self.ensure_one()
        target_status.ensure_one()
        
        # Can't transition to same status
        if self.id == target_status.id:
            return False
        
        # Check if target status requires approval
        if target_status.requires_approval:
            # This would need to check user permissions
            return True  # Simplified for now
        
        # Check lifecycle sequence - generally can only move forward or to specific statuses
        if target_status.sequence < self.sequence:
            # Moving backward in lifecycle - might need special rules
            return target_status.code in ['SUSPENDED', 'TERMINATED']  # Allow suspension/termination
        
        return True
    
    def get_transition_message(self, target_status):
        """Get message about transitioning to target status.
        
        Args:
            target_status (ams.member.status): Target status record
            
        Returns:
            str: Transition message
        """
        self.ensure_one()
        target_status.ensure_one()
        
        if not self.can_transition_to(target_status):
            return _("Transition from %s to %s is not allowed") % (self.name, target_status.name)
        
        messages = []
        
        if target_status.requires_approval:
            messages.append(_("Requires administrative approval"))
        
        if target_status.auto_transition_days and target_status.next_status_id:
            messages.append(_("Will auto-transition to %s after %d days") % 
                          (target_status.next_status_id.name, target_status.auto_transition_days))
        
        if not target_status.is_active:
            messages.append(_("Member will no longer be considered active"))
        
        if not target_status.can_renew:
            messages.append(_("Member will not be able to renew"))
        
        if not target_status.can_purchase:
            messages.append(_("Member will not be able to make purchases"))
        
        if not target_status.allows_portal_access:
            messages.append(_("Portal access will be disabled"))
        
        return " • ".join(messages) if messages else _("No restrictions")
    
    @api.model
    def get_active_statuses(self):
        """Get all statuses that count as active membership."""
        return self.search([('is_active', '=', True)])
    
    @api.model
    def get_renewable_statuses(self):
        """Get all statuses that allow renewal."""
        return self.search([('can_renew', '=', True)])
    
    @api.model
    def get_default_status(self):
        """Get the default status for new members."""
        # Look for a status with code 'PENDING' or 'ACTIVE', or lowest sequence
        default_status = self.search([('code', 'in', ['PENDING', 'ACTIVE'])], limit=1)
        if not default_status:
            default_status = self.search([], order='sequence', limit=1)
        return default_status
    
    def action_view_members(self):
        """Open view of members with this status."""
        self.ensure_one()
        
        # This will be implemented when member model is available
        return {
            'type': 'ir.actions.act_window',
            'name': _('Members - %s') % self.name,
            'res_model': 'ams.member',  # Will be available in future module
            'view_mode': 'tree,form',
            'domain': [('status_id', '=', self.id)],
            'context': {'default_status_id': self.id},
        }
    
    def action_process_auto_transitions(self):
        """Process automatic status transitions for eligible members."""
        # This will be implemented when member model is available
        # Should be called by scheduled action
        pass
    
    # ========================================================================
    # UTILITY METHODS
    # ========================================================================
    
    def name_get(self):
        """Custom name display."""
        result = []
        for record in self:
            name = record.name
            if record.code:
                name = f"[{record.code}] {name}"
            if not record.is_active:
                name = f"{name} (Inactive)"
            result.append((record.id, name))
        return result