# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class AMSCancellationReason(models.Model):
    """Standardized reasons for participation cancellation and termination."""
    
    _name = 'ams.cancellation.reason'
    _inherit = ['mail.thread']
    _description = 'AMS Cancellation Reason'
    _order = 'sequence, category, name'
    _rec_name = 'display_name'

    # ========================================================================
    # CORE FIELDS
    # ========================================================================

    name = fields.Char(
        string="Reason Name",
        required=True,
        tracking=True,
        help="Display name for this cancellation reason"
    )

    code = fields.Char(
        string="Code",
        required=True,
        tracking=True,
        help="Unique identifier code for this reason"
    )

    category = fields.Selection([
        ('voluntary', 'Voluntary'),
        ('involuntary', 'Involuntary'),
        ('administrative', 'Administrative'),
        ('system', 'System Generated'),
        ('other', 'Other')
    ], string="Category", required=True, default='voluntary', tracking=True,
       help="Classification of cancellation reason")

    description = fields.Text(
        string="Description",
        help="Detailed description of this cancellation reason"
    )

    sequence = fields.Integer(
        string="Display Order",
        default=10,
        help="Order in which this reason appears in lists"
    )

    active = fields.Boolean(
        string="Active",
        default=True,
        tracking=True,
        help="Whether this reason is available for selection"
    )

    # ========================================================================
    # CONFIGURATION FIELDS
    # ========================================================================

    applies_to_membership = fields.Boolean(
        string="Applies to Membership",
        default=True,
        help="This reason can be used for membership cancellations"
    )

    applies_to_chapter = fields.Boolean(
        string="Applies to Chapters",
        default=True,
        help="This reason can be used for chapter membership cancellations"
    )

    applies_to_committee = fields.Boolean(
        string="Applies to Committees",
        default=True,
        help="This reason can be used for committee position cancellations"
    )

    applies_to_event = fields.Boolean(
        string="Applies to Events",
        default=False,
        help="This reason can be used for event attendance cancellations"
    )

    applies_to_course = fields.Boolean(
        string="Applies to Courses",
        default=False,
        help="This reason can be used for course enrollment cancellations"
    )

    # ========================================================================
    # BUSINESS IMPACT FIELDS
    # ========================================================================

    immediate_termination = fields.Boolean(
        string="Immediate Termination",
        default=False,
        help="Participation ends immediately when this reason is used"
    )

    allows_refund = fields.Boolean(
        string="Allows Refund",
        default=True,
        help="Member may be eligible for refund with this reason"
    )

    requires_approval = fields.Boolean(
        string="Requires Approval",
        default=False,
        help="Using this reason requires administrative approval"
    )

    blocks_rejoining = fields.Boolean(
        string="Blocks Rejoining",
        default=False,
        help="Member cannot rejoin after using this reason"
    )

    requires_documentation = fields.Boolean(
        string="Requires Documentation",
        default=False,
        help="Additional documentation is required when using this reason"
    )

    # ========================================================================
    # WORKFLOW FIELDS
    # ========================================================================

    notification_template_id = fields.Many2one(
        'mail.template',
        string="Notification Template",
        help="Email template to send when this reason is used"
    )

    follow_up_days = fields.Integer(
        string="Follow-up After (Days)",
        default=0,
        help="Days to wait before follow-up action (0 = no follow-up)"
    )

    escalation_user_id = fields.Many2one(
        'res.users',
        string="Escalation User",
        help="User to notify for approval or review when this reason is used"
    )

    # ========================================================================
    # COMPUTED FIELDS
    # ========================================================================

    display_name = fields.Char(
        string="Display Name",
        compute='_compute_display_name',
        store=True,
        help="Human-readable name with category"
    )

    usage_count = fields.Integer(
        string="Usage Count",
        compute='_compute_usage_count',
        help="Number of times this reason has been used"
    )

    applicable_types = fields.Char(
        string="Applicable Types",
        compute='_compute_applicable_types',
        help="List of participation types this reason applies to"
    )

    impact_summary = fields.Char(
        string="Impact Summary",
        compute='_compute_impact_summary',
        help="Summary of business impacts when this reason is used"
    )

    # ========================================================================
    # CONSTRAINTS
    # ========================================================================

    _sql_constraints = [
        ('code_unique', 'UNIQUE(code)', 'Cancellation reason code must be unique!'),
        ('sequence_positive', 'CHECK(sequence >= 0)', 'Sequence must be non-negative!'),
        ('follow_up_days_positive', 'CHECK(follow_up_days >= 0)', 'Follow-up days must be non-negative!'),
    ]

    # ========================================================================
    # COMPUTE METHODS
    # ========================================================================

    @api.depends('name', 'code', 'category')
    def _compute_display_name(self):
        """Compute display name with category and code."""
        for record in self:
            if record.name and record.category:
                category_display = dict(record._fields['category'].selection).get(record.category, '')
                if record.code:
                    record.display_name = f"[{record.code}] {record.name} ({category_display})"
                else:
                    record.display_name = f"{record.name} ({category_display})"
            else:
                record.display_name = record.name or "Unnamed Reason"

    def _compute_usage_count(self):
        """Compute how many times this reason has been used."""
        for record in self:
            # Count participations using this reason
            count = self.env['ams.participation'].search_count([
                ('cancellation_reason_id', '=', record.id)
            ])
            record.usage_count = count

    @api.depends('applies_to_membership', 'applies_to_chapter', 'applies_to_committee', 
                 'applies_to_event', 'applies_to_course')
    def _compute_applicable_types(self):
        """Compute list of applicable participation types."""
        for record in self:
            types = []
            if record.applies_to_membership:
                types.append('Membership')
            if record.applies_to_chapter:
                types.append('Chapter')
            if record.applies_to_committee:
                types.append('Committee')
            if record.applies_to_event:
                types.append('Event')
            if record.applies_to_course:
                types.append('Course')
            
            record.applicable_types = ', '.join(types) if types else 'None'

    @api.depends('immediate_termination', 'allows_refund', 'requires_approval', 
                 'blocks_rejoining', 'requires_documentation')
    def _compute_impact_summary(self):
        """Compute summary of business impacts."""
        for record in self:
            impacts = []
            
            if record.immediate_termination:
                impacts.append('Immediate termination')
            if record.allows_refund:
                impacts.append('Refund eligible')
            if record.requires_approval:
                impacts.append('Approval required')
            if record.blocks_rejoining:
                impacts.append('Blocks rejoining')
            if record.requires_documentation:
                impacts.append('Documentation required')
            
            record.impact_summary = ' • '.join(impacts) if impacts else 'Standard processing'

    # ========================================================================
    # CONSTRAINT METHODS
    # ========================================================================

    @api.constrains('code')
    def _check_code_format(self):
        """Validate code format."""
        for record in self:
            if record.code:
                if not record.code.replace('_', '').replace('-', '').isalnum():
                    raise ValidationError(_("Code can only contain letters, numbers, underscores, and hyphens"))
                if len(record.code) > 20:
                    raise ValidationError (_("Code cannot be longer than 20 characters"))

    @api.constrains('applies_to_membership', 'applies_to_chapter', 'applies_to_committee',
                    'applies_to_event', 'applies_to_course')
    def _check_applies_to_something(self):
        """Ensure reason applies to at least one participation type."""
        for record in self:
            if not any([
                record.applies_to_membership,
                record.applies_to_chapter,
                record.applies_to_committee,
                record.applies_to_event,
                record.applies_to_course
            ]):
                raise ValidationError(_("Cancellation reason must apply to at least one participation type"))

    @api.constrains('category', 'immediate_termination', 'blocks_rejoining')
    def _check_category_consistency(self):
        """Validate consistency between category and impact settings."""
        for record in self:
            # System reasons should typically have immediate termination
            if record.category == 'system' and not record.immediate_termination:
                # Warning only, not blocking
                pass
            
            # Involuntary reasons typically block rejoining
            if record.category == 'involuntary' and record.allows_refund:
                # This might be unusual but not invalid
                pass

    # ========================================================================
    # ONCHANGE METHODS
    # ========================================================================

    @api.onchange('name')
    def _onchange_name(self):
        """Auto-generate code from name if code is empty."""
        if self.name and not self.code:
            # Generate code from name: "Non-payment" -> "NON_PAYMENT"
            self.code = self.name.upper().replace(' ', '_').replace('-', '_')
            # Remove special characters except underscores
            self.code = ''.join(c for c in self.code if c.isalnum() or c == '_')
            # Truncate to reasonable length
            if len(self.code) > 20:
                self.code = self.code[:20]

    @api.onchange('category')
    def _onchange_category(self):
        """Set defaults based on category."""
        if self.category == 'involuntary':
            self.immediate_termination = True
            self.allows_refund = False
            self.requires_approval = True
            self.blocks_rejoining = True
            self.requires_documentation = True
        elif self.category == 'system':
            self.immediate_termination = True
            self.allows_refund = False
            self.requires_approval = False
            self.requires_documentation = False
        elif self.category == 'administrative':
            self.immediate_termination = False
            self.allows_refund = True
            self.requires_approval = True
            self.requires_documentation = True
        elif self.category == 'voluntary':
            self.immediate_termination = False
            self.allows_refund = True
            self.requires_approval = False
            self.blocks_rejoining = False

    # ========================================================================
    # CRUD METHODS
    # ========================================================================

    @api.model_create_multi
    def create(self, vals_list):
        """Override create to set defaults."""
        for vals in vals_list:
            # Set sequence if not provided
            if 'sequence' not in vals or not vals['sequence']:
                # Get highest sequence for same category + 10
                category = vals.get('category', 'voluntary')
                last_sequence = self.search([
                    ('category', '=', category)
                ], order='sequence desc', limit=1).sequence or 0
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

    @api.model
    def get_applicable_reasons(self, participation_type, category=None):
        """Get cancellation reasons applicable to a participation type.
        
        Args:
            participation_type (str): Type of participation
            category (str, optional): Filter by reason category
            
        Returns:
            recordset: Applicable cancellation reasons
        """
        domain = [('active', '=', True)]
        
        # Add participation type filter
        if participation_type == 'membership':
            domain.append(('applies_to_membership', '=', True))
        elif participation_type == 'chapter':
            domain.append(('applies_to_chapter', '=', True))
        elif participation_type == 'committee_position':
            domain.append(('applies_to_committee', '=', True))
        elif participation_type == 'event_attendance':
            domain.append(('applies_to_event', '=', True))
        elif participation_type == 'course_enrollment':
            domain.append(('applies_to_course', '=', True))
        
        # Add category filter
        if category:
            domain.append(('category', '=', category))
        
        return self.search(domain)

    def get_cancellation_workflow(self):
        """Get workflow configuration for this cancellation reason.
        
        Returns:
            dict: Workflow configuration
        """
        self.ensure_one()
        
        return {
            'immediate_termination': self.immediate_termination,
            'allows_refund': self.allows_refund,
            'requires_approval': self.requires_approval,
            'requires_documentation': self.requires_documentation,
            'blocks_rejoining': self.blocks_rejoining,
            'notification_template_id': self.notification_template_id.id if self.notification_template_id else False,
            'follow_up_days': self.follow_up_days,
            'escalation_user_id': self.escalation_user_id.id if self.escalation_user_id else False,
        }

    def action_view_participations(self):
        """Action to view participations using this reason."""
        self.ensure_one()
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Participations - %s') % self.name,
            'res_model': 'ams.participation',
            'view_mode': 'list,form',
            'domain': [('cancellation_reason_id', '=', self.id)],
            'context': {'default_cancellation_reason_id': self.id},
        }

    @api.model
    def get_usage_statistics(self, date_from=None, date_to=None):
        """Get usage statistics for all cancellation reasons.
        
        Args:
            date_from (date, optional): Start date filter
            date_to (date, optional): End date filter
            
        Returns:
            dict: Usage statistics
        """
        domain = [('cancellation_reason_id', '!=', False)]
        
        if date_from:
            domain.append(('terminated_date', '>=', date_from))
        if date_to:
            domain.append(('terminated_date', '<=', date_to))
        
        participations = self.env['ams.participation'].search(domain)
        
        # Count by reason
        reason_counts = {}
        category_counts = {}
        
        for participation in participations:
            reason = participation.cancellation_reason_id
            if reason:
                # Count by reason
                reason_key = f"{reason.name} [{reason.code}]"
                reason_counts[reason_key] = reason_counts.get(reason_key, 0) + 1
                
                # Count by category
                category_counts[reason.category] = category_counts.get(reason.category, 0) + 1
        
        return {
            'total_cancellations': len(participations),
            'by_reason': reason_counts,
            'by_category': category_counts,
            'period': {
                'from': date_from,
                'to': date_to
            }
        }

    # ========================================================================
    # UTILITY METHODS
    # ========================================================================

    def name_get(self):
        """Custom name display."""
        result = []
        for record in self:
            result.append((record.id, record.display_name))
        return result

    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        """Custom name search."""
        args = args or []
        
        if name:
            # Search in name, code, and description
            domain = [
                '|', '|',
                ('name', operator, name),
                ('code', operator, name),
                ('description', operator, name)
            ]
            args = domain + args
        
        return self._search(args, limit=limit, access_rights_uid=name_get_uid)