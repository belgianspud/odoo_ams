from odoo import models, fields, api


class ResPartnerParticipation(models.Model):
    """Extend res.partner with comprehensive participation tracking capabilities."""
    _inherit = 'res.partner'

    # ==========================================
    # PARTICIPATION STATISTICS (COMPUTED FIELDS)
    # ==========================================
    
    participation_count = fields.Integer(
        string='Total Participations',
        compute='_compute_participation_stats',
        help='Total number of participations (all statuses)'
    )
    
    active_participation_count = fields.Integer(
        string='Active Participations', 
        compute='_compute_participation_stats',
        help='Number of current active participations'
    )
    
    historical_participation_count = fields.Integer(
        string='Historical Participations',
        compute='_compute_participation_stats',
        help='Number of inactive/historical participations'
    )
    
    has_active_membership = fields.Boolean(
        string='Has Active Membership',
        compute='_compute_participation_stats',
        help='Has at least one active membership participation'
    )
    
    # ==========================================
    # PRIMARY MEMBERSHIP TRACKING
    # ==========================================
    
    primary_membership_id = fields.Many2one(
        'ams.participation',
        string='Primary Membership',
        compute='_compute_primary_membership',
        help='Primary active membership participation'
    )

    # ==========================================
    # PROFESSIONAL ASSOCIATION SPECIFIC FIELDS
    # ==========================================
    
    member_since = fields.Date(
        string='Member Since',
        compute='_compute_member_since',
        help='Date of first participation'
    )
    
    membership_grade = fields.Char(
        string='Membership Grade',
        compute='_compute_membership_grade',
        help='Current membership level/grade'
    )
    
    professional_designation = fields.Char(
        string='Professional Designation',
        compute='_compute_professional_designation',
        help='Professional certifications or designations'
    )
    
    chapter_memberships = fields.Char(
        string='Chapter Affiliations',
        compute='_compute_chapter_memberships',
        help='Active chapter memberships'
    )
    
    committee_roles = fields.Char(
        string='Committee Roles', 
        compute='_compute_committee_roles',
        help='Current committee positions'
    )
    
    continuing_education_status = fields.Selection([
        ('current', 'Current'),
        ('expiring_soon', 'Expiring Soon'),
        ('expired', 'Expired'),
        ('not_required', 'Not Required')
    ], string='CE Status', 
       compute='_compute_ce_status',
       help='Continuing education compliance status')

    # ==========================================
    # DYNAMIC PARTICIPATION RELATIONSHIPS (NON-STORED)
    # ==========================================
    
    active_participation_ids = fields.One2many(
        'ams.participation',
        compute='_compute_active_participation_ids',
        string='Active Participations',
        help='Current active participations (active and grace status)'
    )
    
    historical_participation_ids = fields.One2many(
        'ams.participation',
        compute='_compute_historical_participation_ids', 
        string='Historical Participations',
        help='Inactive/historical participations'
    )

    # ==========================================
    # COMPUTED METHOD DEPENDENCIES
    # ==========================================

    def _compute_participation_stats(self):
        """Compute participation statistics efficiently."""
        # Get all partners and their participations in bulk for efficiency
        if not self:
            return
            
        # Build domain to get all participations for these partners
        individual_partner_ids = self.filtered(lambda p: not p.is_company).ids
        company_partner_ids = self.filtered(lambda p: p.is_company).ids
        
        # Initialize all fields to zero
        for partner in self:
            partner.participation_count = 0
            partner.active_participation_count = 0
            partner.historical_participation_count = 0
            partner.has_active_membership = False
        
        if not individual_partner_ids and not company_partner_ids:
            return
            
        # Query participations in bulk
        domain = []
        if individual_partner_ids:
            domain.append(('partner_id', 'in', individual_partner_ids))
        if company_partner_ids:
            if domain:
                domain = ['|'] + domain + [('company_id', 'in', company_partner_ids)]
            else:
                domain = [('company_id', 'in', company_partner_ids)]
        
        if not domain:
            return
            
        participations = self.env['ams.participation'].search(domain)
        
        # Group participations by partner
        partner_participations = {}
        for participation in participations:
            partner_id = participation.partner_id.id if participation.partner_id else participation.company_id.id
            if partner_id not in partner_participations:
                partner_participations[partner_id] = []
            partner_participations[partner_id].append(participation)
        
        # Calculate stats for each partner
        for partner in self:
            partner_participations_list = partner_participations.get(partner.id, [])
            
            # Total participations
            partner.participation_count = len(partner_participations_list)
            
            # Active participations (active and grace status)
            active_participations = [p for p in partner_participations_list if p.status in ['active', 'grace']]
            partner.active_participation_count = len(active_participations)
            
            # Historical participations
            historical_participations = [p for p in partner_participations_list if p.status not in ['active', 'grace']]
            partner.historical_participation_count = len(historical_participations)
            
            # Has active membership
            active_memberships = [p for p in active_participations if p.participation_type == 'membership']
            partner.has_active_membership = len(active_memberships) > 0

    def _compute_primary_membership(self):
        """Get primary active membership participation."""
        for partner in self:
            if partner.is_company:
                domain = [
                    ('company_id', '=', partner.id),
                    ('participation_type', '=', 'membership'),
                    ('status', 'in', ['active', 'grace'])
                ]
            else:
                domain = [
                    ('partner_id', '=', partner.id),
                    ('participation_type', '=', 'membership'),
                    ('status', 'in', ['active', 'grace'])
                ]
            
            # Get the most recent active membership
            membership = self.env['ams.participation'].search(
                domain, order='status desc, begin_date desc', limit=1
            )
            
            partner.primary_membership_id = membership

    def _compute_member_since(self):
        """Compute earliest participation join date."""
        for partner in self:
            if partner.is_company:
                domain = [('company_id', '=', partner.id)]
            else:
                domain = [('partner_id', '=', partner.id)]
                
            earliest_participation = self.env['ams.participation'].search(
                domain, order='join_date asc', limit=1
            )
            
            partner.member_since = earliest_participation.join_date if earliest_participation else False

    def _compute_membership_grade(self):
        """Compute membership grade from active memberships."""
        for partner in self:
            if partner.primary_membership_id:
                # This would integrate with subscription product names when that module is available
                if partner.primary_membership_id.subscription_product_id:
                    partner.membership_grade = partner.primary_membership_id.subscription_product_id
                else:
                    partner.membership_grade = 'Standard Member'
            else:
                partner.membership_grade = 'Non-Member'

    def _compute_chapter_memberships(self):
        """Compute chapter membership summary."""
        for partner in self:
            if partner.is_company:
                domain = [
                    ('company_id', '=', partner.id),
                    ('participation_type', '=', 'chapter'),
                    ('status', 'in', ['active', 'grace'])
                ]
            else:
                domain = [
                    ('partner_id', '=', partner.id),
                    ('participation_type', '=', 'chapter'),
                    ('status', 'in', ['active', 'grace'])
                ]
                
            chapters = self.env['ams.participation'].search(domain)
            
            if chapters:
                partner.chapter_memberships = f"{len(chapters)} Chapter Membership(s)"
            else:
                partner.chapter_memberships = 'No Chapter Affiliations'

    def _compute_committee_roles(self):
        """Compute committee role summary."""
        for partner in self:
            if partner.is_company:
                domain = [
                    ('company_id', '=', partner.id),
                    ('participation_type', '=', 'committee_position'),
                    ('status', 'in', ['active', 'grace'])
                ]
            else:
                domain = [
                    ('partner_id', '=', partner.id),
                    ('participation_type', '=', 'committee_position'),
                    ('status', 'in', ['active', 'grace'])
                ]
                
            committees = self.env['ams.participation'].search(domain)
            
            if committees:
                partner.committee_roles = f"{len(committees)} Committee Role(s)"
            else:
                partner.committee_roles = 'No Committee Roles'

    def _compute_ce_status(self):
        """Compute continuing education status."""
        for partner in self:
            # This will be enhanced when ams_education_credits module is available
            # For now, set default based on membership status
            if partner.has_active_membership:
                partner.continuing_education_status = 'not_required'
            else:
                partner.continuing_education_status = 'not_required'

    def _compute_professional_designation(self):
        """Compute professional designation - placeholder until proper field is added."""
        for partner in self:
            # For now, return empty string - this will be a stored field later
            partner.professional_designation = ''

    def _compute_active_participation_ids(self):
        """Compute active participations as recordset for XML views."""
        for partner in self:
            if partner.is_company:
                participations = self.env['ams.participation'].search([
                    ('company_id', '=', partner.id),
                    ('status', 'in', ['active', 'grace'])
                ], order='begin_date desc')
            else:
                participations = self.env['ams.participation'].search([
                    ('partner_id', '=', partner.id),
                    ('status', 'in', ['active', 'grace'])
                ], order='begin_date desc')
            partner.active_participation_ids = participations

    def _compute_historical_participation_ids(self):
        """Compute historical participations as recordset for XML views."""
        for partner in self:
            if partner.is_company:
                participations = self.env['ams.participation'].search([
                    ('company_id', '=', partner.id),
                    ('status', 'not in', ['active', 'grace'])
                ], order='terminated_date desc, end_date desc')
            else:
                participations = self.env['ams.participation'].search([
                    ('partner_id', '=', partner.id),
                    ('status', 'not in', ['active', 'grace'])
                ], order='terminated_date desc, end_date desc')
            partner.historical_participation_ids = participations

    # ==========================================
    # RELATIONSHIP PROPERTIES (For backward compatibility)
    # ==========================================

    @property
    def participation_ids(self):
        """Get all participations for this partner (backward compatibility)."""
        if self.is_company:
            return self.env['ams.participation'].search([('company_id', '=', self.id)])
        else:
            return self.env['ams.participation'].search([('partner_id', '=', self.id)])

    # Define computed fields for dynamic relationships
    def _compute_all_participation_ids(self):
        """Compute all participations for this partner."""
        for partner in self:
            if partner.is_company:
                participations = self.env['ams.participation'].search([('company_id', '=', partner.id)])
            else:
                participations = self.env['ams.participation'].search([('partner_id', '=', partner.id)])
            partner.all_participation_ids = participations

    all_participation_ids = fields.One2many(
        'ams.participation',
        compute='_compute_all_participation_ids',
        string='All Participations',
        help='All participations for this partner'
    )

    # ==========================================
    # ACTION METHODS (Referenced in XML views)
    # ==========================================

    def action_view_participations(self):
        """Open participations for this member."""
        self.ensure_one()
        if self.is_company:
            domain = [('company_id', '=', self.id)]
        else:
            domain = [('partner_id', '=', self.id)]
            
        return {
            'name': f'Participations - {self.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'ams.participation',
            'view_mode': 'list,form',
            'domain': domain,
            'context': {
                'default_partner_id': None if self.is_company else self.id,
                'default_company_id': self.id if self.is_company else None,
            },
        }

    def action_view_active_participations(self):
        """Open active participations view."""
        self.ensure_one()
        if self.is_company:
            domain = [
                ('company_id', '=', self.id),
                ('status', 'in', ['active', 'grace'])
            ]
        else:
            domain = [
                ('partner_id', '=', self.id),
                ('status', 'in', ['active', 'grace'])
            ]
            
        return {
            'name': f'Active Participations - {self.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'ams.participation',
            'view_mode': 'list,form',
            'domain': domain,
            'context': {
                'default_partner_id': None if self.is_company else self.id,
                'default_company_id': self.id if self.is_company else None,
            },
        }

    def action_view_all_participations(self):
        """Open all participations view (alias for action_view_participations)."""
        return self.action_view_participations()

    def action_create_participation(self):
        """Quick action to create a new participation."""
        self.ensure_one()
        return {
            'name': f'New Participation - {self.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'ams.participation',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_partner_id': None if self.is_company else self.id,
                'default_company_id': self.id if self.is_company else None,
                'default_participation_type': 'membership',
            },
        }

    def action_export_participation_history(self):
        """Export participation history (placeholder for future reporting module)."""
        self.ensure_one()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Export Available Soon',
                'message': f'Export functionality for {self.name}\'s participation history will be available with the reporting module.',
                'type': 'info'
            }
        }

    # ==========================================
    # UTILITY METHODS
    # ==========================================

    def get_participation_summary(self):
        """Get participation summary for this partner."""
        self.ensure_one()
        return {
            'total_participations': self.participation_count,
            'active_participations': self.active_participation_count,
            'historical_participations': self.historical_participation_count,
            'has_active_membership': self.has_active_membership,
            'member_since': self.member_since,
            'membership_grade': self.membership_grade,
        }

    def has_participation_type(self, participation_type, status=None):
        """Check if partner has specific participation type."""
        self.ensure_one()
        
        if self.is_company:
            domain = [
                ('company_id', '=', self.id),
                ('participation_type', '=', participation_type)
            ]
        else:
            domain = [
                ('partner_id', '=', self.id),
                ('participation_type', '=', participation_type)
            ]
            
        if status:
            if isinstance(status, list):
                domain.append(('status', 'in', status))
            else:
                domain.append(('status', '=', status))
        
        return bool(self.env['ams.participation'].search_count(domain))

    def get_active_memberships(self):
        """Get all active membership participations."""
        self.ensure_one()
        
        if self.is_company:
            domain = [
                ('company_id', '=', self.id),
                ('participation_type', '=', 'membership'),
                ('status', 'in', ['active', 'grace'])
            ]
        else:
            domain = [
                ('partner_id', '=', self.id),
                ('participation_type', '=', 'membership'),
                ('status', 'in', ['active', 'grace'])
            ]
            
        return self.env['ams.participation'].search(domain)

    def get_participation_history(self):
        """Get participation history for this partner."""
        self.ensure_one()
        
        if self.is_company:
            domain = [('participation_id.company_id', '=', self.id)]
        else:
            domain = [('participation_id.partner_id', '=', self.id)]
            
        return self.env['ams.participation.history'].search(
            domain, order='change_date desc'
        )