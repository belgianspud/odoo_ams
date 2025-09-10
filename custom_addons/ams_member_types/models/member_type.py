# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class AMSMemberType(models.Model):
    """Member type classification for association members."""
    
    _name = 'ams.member.type'
    _inherit = ['mail.thread']
    _description = 'AMS Member Type'
    _order = 'sequence, name'
    
    # ========================================================================
    # FIELDS
    # ========================================================================
    
    name = fields.Char(
        string="Type Name",
        required=True,
        help="Display name for this member type"
    )
    
    code = fields.Char(
        string="Code",
        required=True,
        help="Unique code for this member type"
    )
    
    is_individual = fields.Boolean(
        string="For Individuals",
        default=True,
        help="This member type is available for individual members"
    )
    
    is_organization = fields.Boolean(
        string="For Organizations",
        default=False,
        help="This member type is available for organizational members"
    )
    
    sequence = fields.Integer(
        string="Display Order",
        default=10,
        help="Order in which this type appears in lists"
    )
    
    description = fields.Text(
        string="Description",
        help="Detailed description of this member type"
    )
    
    active = fields.Boolean(
        string="Active",
        default=True,
        help="Inactive member types cannot be assigned to new members"
    )
    
    # ========================================================================
    # ELIGIBILITY RULES
    # ========================================================================
    
    min_age = fields.Integer(
        string="Minimum Age",
        help="Minimum age required for this member type (0 = no minimum)"
    )
    
    max_age = fields.Integer(
        string="Maximum Age",
        help="Maximum age allowed for this member type (0 = no maximum)"
    )
    
    requires_verification = fields.Boolean(
        string="Requires Verification",
        default=False,
        help="Members of this type require manual verification before activation"
    )
    
    auto_approve = fields.Boolean(
        string="Auto-approve",
        default=True,
        help="Automatically approve membership applications for this type"
    )
    
    # ========================================================================
    # COMPUTED FIELDS
    # ========================================================================
    
    member_count = fields.Integer(
        string="Current Members",
        compute='_compute_member_count',
        help="Number of active members with this type"
    )
    
    # ========================================================================
    # SQL CONSTRAINTS
    # ========================================================================
    
    _sql_constraints = [
        ('code_unique', 'UNIQUE(code)', 'Member type code must be unique!'),
        ('name_unique', 'UNIQUE(name)', 'Member type name must be unique!'),
        ('min_age_positive', 'CHECK(min_age >= 0)', 'Minimum age must be positive!'),
        ('max_age_positive', 'CHECK(max_age >= 0)', 'Maximum age must be positive!'),
    ]
    
    # ========================================================================
    # CONSTRAINT METHODS
    # ========================================================================
    
    @api.constrains('min_age', 'max_age')
    def _check_age_range(self):
        """Validate age range is logical."""
        for record in self:
            if record.min_age and record.max_age and record.min_age > record.max_age:
                raise ValidationError(_("Minimum age cannot be greater than maximum age"))
    
    @api.constrains('is_individual', 'is_organization')
    def _check_member_classification(self):
        """Ensure at least one classification is selected."""
        for record in self:
            if not record.is_individual and not record.is_organization:
                raise ValidationError(_("Member type must be available for individuals, organizations, or both"))
    
    @api.constrains('code')
    def _check_code_format(self):
        """Validate code format."""
        for record in self:
            if record.code:
                if not record.code.replace('_', '').replace('-', '').isalnum():
                    raise ValidationError(_("Code can only contain letters, numbers, underscores, and hyphens"))
                if len(record.code) > 20:
                    raise ValidationError(_("Code cannot be longer than 20 characters"))
    
    @api.constrains('auto_approve', 'requires_verification')
    def _check_approval_logic(self):
        """Validate approval and verification logic."""
        for record in self:
            if record.auto_approve and record.requires_verification:
                raise ValidationError(_(
                    "Cannot auto-approve members who require verification. "
                    "Please choose either auto-approval or verification requirement."
                ))
    
    # ========================================================================
    # COMPUTE METHODS
    # ========================================================================
    
    def _compute_member_count(self):
        """Compute current member count for this type."""
        # This will be implemented when member model is available
        for record in self:
            record.member_count = 0
    
    # ========================================================================
    # ONCHANGE METHODS
    # ========================================================================
    
    @api.onchange('name')
    def _onchange_name(self):
        """Auto-generate code from name if code is empty."""
        if self.name and not self.code:
            # Generate code from name: "Student Member" -> "STUDENT_MEMBER"
            self.code = self.name.upper().replace(' ', '_').replace('-', '_')
            # Remove special characters except underscores
            self.code = ''.join(c for c in self.code if c.isalnum() or c == '_')
    
    @api.onchange('requires_verification')
    def _onchange_requires_verification(self):
        """Disable auto-approve when verification is required."""
        if self.requires_verification:
            self.auto_approve = False
    
    @api.onchange('auto_approve')
    def _onchange_auto_approve(self):
        """Disable verification requirement when auto-approve is enabled."""
        if self.auto_approve:
            self.requires_verification = False
    
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
    
    def check_age_eligibility(self, age):
        """Check if given age meets eligibility requirements.
        
        Args:
            age (int): Age to check
            
        Returns:
            bool: True if age is eligible, False otherwise
        """
        self.ensure_one()
        
        if self.min_age and age < self.min_age:
            return False
        
        if self.max_age and age > self.max_age:
            return False
        
        return True
    
    def get_eligibility_message(self, age=None):
        """Get human-readable eligibility message.
        
        Args:
            age (int, optional): Age to check against requirements
            
        Returns:
            str: Eligibility message
        """
        self.ensure_one()
        
        messages = []
        
        # Age requirements
        if self.min_age and self.max_age:
            messages.append(_("Ages %d-%d") % (self.min_age, self.max_age))
        elif self.min_age:
            messages.append(_("Minimum age %d") % self.min_age)
        elif self.max_age:
            messages.append(_("Maximum age %d") % self.max_age)
        
        # Member classification
        classifications = []
        if self.is_individual:
            classifications.append(_("Individuals"))
        if self.is_organization:
            classifications.append(_("Organizations"))
        if classifications:
            messages.append(_("Available for: %s") % ", ".join(classifications))
        
        # Approval requirements
        if self.requires_verification:
            messages.append(_("Requires verification"))
        elif self.auto_approve:
            messages.append(_("Auto-approved"))
        
        # Check specific age if provided
        if age is not None and not self.check_age_eligibility(age):
            messages.append(_("⚠ Age %d does not meet requirements") % age)
        
        return " • ".join(messages) if messages else _("No specific requirements")
    
    @api.model
    def get_available_types(self, is_individual=None, age=None):
        """Get member types available for given criteria.
        
        Args:
            is_individual (bool, optional): True for individual, False for organization
            age (int, optional): Age to check eligibility
            
        Returns:
            recordset: Available member types
        """
        domain = [('active', '=', True)]
        
        # Filter by member classification
        if is_individual is True:
            domain.append(('is_individual', '=', True))
        elif is_individual is False:
            domain.append(('is_organization', '=', True))
        
        # Get types
        types = self.search(domain)
        
        # Filter by age if provided
        if age is not None:
            types = types.filtered(lambda t: t.check_age_eligibility(age))
        
        return types
    
    def action_view_members(self):
        """Open view of members with this type."""
        self.ensure_one()
        
        # This will be implemented when member model is available
        return {
            'type': 'ir.actions.act_window',
            'name': _('Members - %s') % self.name,
            'res_model': 'ams.member',  # Will be available in future module
            'view_mode': 'list,form',
            'domain': [('member_type_id', '=', self.id)],
            'context': {'default_member_type_id': self.id},
        }
    
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
            result.append((record.id, name))
        return result