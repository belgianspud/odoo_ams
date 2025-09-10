# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError


class AMSSubscriptionProduct(models.Model):
    """Placeholder model for subscription products until full billing module is available."""
    
    _name = 'ams.subscription.product'
    _description = 'AMS Subscription Product (Placeholder)'
    _inherit = ['mail.thread']
    _order = 'sequence, name'
    _rec_name = 'display_name'

    # ========================================================================
    # CORE FIELDS
    # ========================================================================

    name = fields.Char(
        string="Product Name",
        required=True,
        tracking=True,
        help="Name of the subscription product"
    )

    code = fields.Char(
        string="Product Code",
        required=True,
        tracking=True,
        help="Unique identifier for this product"
    )

    active = fields.Boolean(
        string="Active",
        default=True,
        tracking=True,
        help="Whether this product is available for new subscriptions"
    )

    sequence = fields.Integer(
        string="Sequence",
        default=10,
        help="Display order"
    )

    description = fields.Text(
        string="Description",
        help="Detailed description of the subscription product"
    )

    # ========================================================================
    # PRODUCT CLASSIFICATION
    # ========================================================================

    product_type = fields.Selection([
        ('membership', 'Membership'),
        ('chapter', 'Chapter Membership'),
        ('course', 'Course/Training'),
        ('event', 'Event Registration'),
        ('service', 'Service/Benefit'),
        ('other', 'Other')
    ], string="Product Type", default='membership', required=True,
       help="Type of subscription product")

    is_renewable = fields.Boolean(
        string="Is Renewable",
        default=True,
        help="Whether this product can be renewed"
    )

    is_membership_product = fields.Boolean(
        string="Is Membership Product",
        default=True,
        help="Whether this is a core membership product"
    )

    # ========================================================================
    # BASIC PRICING (Placeholder until full billing)
    # ========================================================================

    list_price = fields.Monetary(
        string="List Price",
        default=0.0,
        currency_field='currency_id',
        help="Standard price for this product"
    )

    currency_id = fields.Many2one(
        'res.currency',
        string="Currency",
        default=lambda self: self.env.company.currency_id,
        help="Currency for pricing"
    )

    # ========================================================================
    # TERM CONFIGURATION
    # ========================================================================

    term_length = fields.Integer(
        string="Term Length (Days)",
        default=365,
        help="Length of subscription term in days"
    )

    grace_period_days = fields.Integer(
        string="Grace Period (Days)",
        default=30,
        help="Grace period after expiration"
    )

    auto_renew_default = fields.Boolean(
        string="Auto-Renew by Default",
        default=False,
        help="Whether auto-renewal is enabled by default"
    )

    # ========================================================================
    # COMPUTED FIELDS
    # ========================================================================

    display_name = fields.Char(
        string="Display Name",
        compute='_compute_display_name',
        store=True,
        help="Product display name with code"
    )

    participation_count = fields.Integer(
        string="Active Participations",
        compute='_compute_participation_count',
        help="Number of active participations using this product"
    )

    # ========================================================================
    # CONSTRAINTS
    # ========================================================================

    _sql_constraints = [
        ('code_unique', 'UNIQUE(code)', 'Product code must be unique!'),
        ('term_length_positive', 'CHECK(term_length > 0)', 'Term length must be positive!'),
        ('list_price_positive', 'CHECK(list_price >= 0)', 'List price must be non-negative!'),
    ]

    # ========================================================================
    # COMPUTE METHODS
    # ========================================================================

    @api.depends('name', 'code')
    def _compute_display_name(self):
        """Compute display name with code."""
        for record in self:
            if record.code and record.name:
                record.display_name = f"[{record.code}] {record.name}"
            else:
                record.display_name = record.name or "Unnamed Product"

    def _compute_participation_count(self):
        """Count active participations using this product."""
        for record in self:
            count = self.env['ams.participation'].search_count([
                ('subscription_product_id', '=', record.id),
                ('status', '=', 'active')
            ])
            record.participation_count = count

    # ========================================================================
    # ONCHANGE METHODS
    # ========================================================================

    @api.onchange('name')
    def _onchange_name(self):
        """Auto-generate code from name if code is empty."""
        if self.name and not self.code:
            # Generate code from name
            self.code = self.name.upper().replace(' ', '_')
            # Keep only alphanumeric and underscore
            self.code = ''.join(c for c in self.code if c.isalnum() or c == '_')
            # Truncate to reasonable length
            if len(self.code) > 20:
                self.code = self.code[:20]

    @api.onchange('product_type')
    def _onchange_product_type(self):
        """Set defaults based on product type."""
        if self.product_type == 'membership':
            self.is_membership_product = True
            self.is_renewable = True
            self.term_length = 365
        elif self.product_type == 'chapter':
            self.is_membership_product = False
            self.is_renewable = True
            self.term_length = 365
        elif self.product_type == 'course':
            self.is_membership_product = False
            self.is_renewable = False
            self.term_length = 90
        elif self.product_type == 'event':
            self.is_membership_product = False
            self.is_renewable = False
            self.term_length = 1

    # ========================================================================
    # BUSINESS METHODS
    # ========================================================================

    def action_view_participations(self):
        """View participations using this product."""
        self.ensure_one()
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Participations - %s') % self.display_name,
            'res_model': 'ams.participation',
            'view_mode': 'list,form',
            'domain': [('subscription_product_id', '=', self.id)],
            'context': {'default_subscription_product_id': self.id},
        }

    def get_pricing_info(self, partner_id=None):
        """Get pricing information (placeholder for full billing module)."""
        self.ensure_one()
        
        return {
            'list_price': self.list_price,
            'currency': self.currency_id.name,
            'term_length': self.term_length,
            'is_renewable': self.is_renewable,
            'message': _('Full pricing with discounts will be available when billing module is installed')
        }


class AMSCommitteePosition(models.Model):
    """Placeholder model for committee positions until committee module is available."""
    
    _name = 'ams.committee.position'
    _description = 'AMS Committee Position (Placeholder)'
    _inherit = ['mail.thread']
    _order = 'committee_name, sequence, name'
    _rec_name = 'display_name'

    # ========================================================================
    # CORE FIELDS
    # ========================================================================

    name = fields.Char(
        string="Position Name",
        required=True,
        tracking=True,
        help="Name of the committee position"
    )

    code = fields.Char(
        string="Position Code",
        required=True,
        tracking=True,
        help="Unique identifier for this position"
    )

    active = fields.Boolean(
        string="Active",
        default=True,
        tracking=True,
        help="Whether this position is available"
    )

    sequence = fields.Integer(
        string="Sequence",
        default=10,
        help="Display order within committee"
    )

    description = fields.Text(
        string="Description",
        help="Detailed description of the position responsibilities"
    )

    # ========================================================================
    # COMMITTEE INFORMATION
    # ========================================================================

    committee_name = fields.Char(
        string="Committee Name",
        required=True,
        help="Name of the committee (placeholder until committee module)"
    )

    committee_type = fields.Selection([
        ('standing', 'Standing Committee'),
        ('special', 'Special Committee'),
        ('board', 'Board Position'),
        ('executive', 'Executive Position'),
        ('advisory', 'Advisory Position')
    ], string="Committee Type", default='standing', required=True,
       help="Type of committee or position")

    # ========================================================================
    # POSITION DETAILS
    # ========================================================================

    is_executive = fields.Boolean(
        string="Executive Position",
        default=False,
        help="Whether this is an executive/leadership position"
    )

    is_voting = fields.Boolean(
        string="Voting Position",
        default=True,
        help="Whether this position has voting rights"
    )

    requires_election = fields.Boolean(
        string="Requires Election",
        default=False,
        help="Whether this position requires formal election"
    )

    term_length_months = fields.Integer(
        string="Term Length (Months)",
        default=12,
        help="Length of term in months"
    )

    max_consecutive_terms = fields.Integer(
        string="Max Consecutive Terms",
        default=0,
        help="Maximum consecutive terms (0 = no limit)"
    )

    # ========================================================================
    # REQUIREMENTS
    # ========================================================================

    minimum_membership_months = fields.Integer(
        string="Minimum Membership (Months)",
        default=0,
        help="Minimum months of membership required"
    )

    required_member_type = fields.Char(
        string="Required Member Type",
        help="Required member type/classification (placeholder)"
    )

    requires_approval = fields.Boolean(
        string="Requires Approval",
        default=True,
        help="Whether appointment requires approval"
    )

    # ========================================================================
    # COMPUTED FIELDS
    # ========================================================================

    display_name = fields.Char(
        string="Display Name",
        compute='_compute_display_name',
        store=True,
        help="Position display name with committee"
    )

    current_holder_count = fields.Integer(
        string="Current Holders",
        compute='_compute_current_holder_count',
        help="Number of people currently in this position"
    )

    # ========================================================================
    # CONSTRAINTS
    # ========================================================================

    _sql_constraints = [
        ('code_unique', 'UNIQUE(code)', 'Position code must be unique!'),
        ('term_length_positive', 'CHECK(term_length_months > 0)', 'Term length must be positive!'),
        ('max_terms_positive', 'CHECK(max_consecutive_terms >= 0)', 'Max consecutive terms must be non-negative!'),
    ]

    # ========================================================================
    # COMPUTE METHODS
    # ========================================================================

    @api.depends('name', 'committee_name', 'code')
    def _compute_display_name(self):
        """Compute display name with committee and code."""
        for record in self:
            if record.committee_name and record.name:
                display = f"{record.committee_name} - {record.name}"
                if record.code:
                    display = f"[{record.code}] {display}"
                record.display_name = display
            else:
                record.display_name = record.name or "Unnamed Position"

    def _compute_current_holder_count(self):
        """Count current position holders."""
        for record in self:
            count = self.env['ams.participation'].search_count([
                ('committee_position_id', '=', record.id),
                ('status', '=', 'active'),
                ('participation_type', '=', 'committee_position')
            ])
            record.current_holder_count = count

    # ========================================================================
    # ONCHANGE METHODS
    # ========================================================================

    @api.onchange('name', 'committee_name')
    def _onchange_name_committee(self):
        """Auto-generate code from name and committee if code is empty."""
        if self.name and self.committee_name and not self.code:
            # Generate code from committee and position name
            committee_code = self.committee_name[:3].upper()
            position_code = self.name.upper().replace(' ', '_')
            self.code = f"{committee_code}_{position_code}"
            # Keep only alphanumeric and underscore
            self.code = ''.join(c for c in self.code if c.isalnum() or c == '_')
            # Truncate to reasonable length
            if len(self.code) > 20:
                self.code = self.code[:20]

    @api.onchange('committee_type')
    def _onchange_committee_type(self):
        """Set defaults based on committee type."""
        if self.committee_type == 'board':
            self.is_executive = True
            self.is_voting = True
            self.requires_election = True
            self.term_length_months = 24
            self.requires_approval = True
        elif self.committee_type == 'executive':
            self.is_executive = True
            self.is_voting = True
            self.requires_election = True
            self.term_length_months = 12
            self.requires_approval = True
        elif self.committee_type == 'advisory':
            self.is_executive = False
            self.is_voting = False
            self.requires_election = False
            self.term_length_months = 12
            self.requires_approval = True

    # ========================================================================
    # BUSINESS METHODS
    # ========================================================================

    def action_view_participations(self):
        """View participations for this position."""
        self.ensure_one()
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Position Holders - %s') % self.display_name,
            'res_model': 'ams.participation',
            'view_mode': 'list,form',
            'domain': [
                ('committee_position_id', '=', self.id),
                ('participation_type', '=', 'committee_position')
            ],
            'context': {
                'default_committee_position_id': self.id,
                'default_participation_type': 'committee_position'
            },
        }

    def check_eligibility(self, partner_id):
        """Check if partner is eligible for this position (placeholder)."""
        self.ensure_one()
        
        # Basic eligibility checks (placeholder for full committee module)
        partner = self.env['res.partner'].browse(partner_id)
        
        issues = []
        
        # Check if partner exists and is a member
        if not partner.exists():
            issues.append("Partner not found")
            return {'eligible': False, 'issues': issues}
        
        if not getattr(partner, 'is_member', False):
            issues.append("Must be an association member")
        
        # Check minimum membership requirement
        if self.minimum_membership_months > 0:
            if hasattr(partner, 'member_since') and partner.member_since:
                from datetime import date
                months_member = (date.today() - partner.member_since).days / 30.44
                if months_member < self.minimum_membership_months:
                    issues.append(f"Requires {self.minimum_membership_months} months of membership")
        
        # Check for existing active position
        existing_position = self.env['ams.participation'].search([
            ('partner_id', '=', partner_id),
            ('committee_position_id', '=', self.id),
            ('status', '=', 'active'),
            ('participation_type', '=', 'committee_position')
        ])
        
        if existing_position:
            issues.append("Already holds this position")
        
        return {
            'eligible': len(issues) == 0,
            'issues': issues,
            'message': 'Full eligibility checking will be available when committee module is installed'
        }

    def get_position_info(self):
        """Get comprehensive position information."""
        self.ensure_one()
        
        return {
            'name': self.name,
            'committee': self.committee_name,
            'type': self.committee_type,
            'is_executive': self.is_executive,
            'is_voting': self.is_voting,
            'term_length': self.term_length_months,
            'requires_election': self.requires_election,
            'requires_approval': self.requires_approval,
            'current_holders': self.current_holder_count,
            'minimum_membership_months': self.minimum_membership_months,
        }